import os
import asyncio
import logging
import secrets
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv
import shutil
import uuid

from utils.pdf_reader import PDFReader
from utils.skill_extractor import SkillExtractor
from utils.ats_score import ATSScoreCalculator
from utils.candidate_summary import CandidateSummaryGenerator
from utils.interview_generator import InterviewGenerator
from utils.rag_engine import RAGEngine
from utils.job_search import JobSearchEngine
from utils.resume_tailor import ResumeTailor
from utils.resume_builder import ResumeBuilder

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Resume Screening & Interview Assistant")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

pdf_reader = PDFReader()
skill_extractor = SkillExtractor()
ats_calculator = ATSScoreCalculator()
summary_generator = CandidateSummaryGenerator()
interview_generator = InterviewGenerator()
rag_engine = RAGEngine()
job_search_engine = JobSearchEngine()
resume_tailor = ResumeTailor()

TAILORED_DIR = Path(os.getenv("TAILORED_DIR", "./tailored_output"))
TAILORED_DIR.mkdir(exist_ok=True)

# in-memory store of raw resume text + tailored results, keyed by id (swap for a DB in production)
_resume_text_cache: Dict[str, str] = {}
_tailored_cache: Dict[str, Dict] = {}

# --- auth: single shared login from env, in-memory session tokens (swap for a DB in production)
SESSION_COOKIE = "ra_session"
_session_tokens: set = set()

def _app_credentials() -> tuple:
    return os.getenv("APP_USERNAME", "demo@resume.ai"), os.getenv("APP_PASSWORD", "resume123")

def _is_authenticated(request: Request) -> bool:
    return request.cookies.get(SESSION_COOKIE, "") in _session_tokens

class ChatRequest(BaseModel):
    question: str
    resume_id: str

class JobSearchRequest(BaseModel):
    resume_id: str
    keywords: str
    location: str = ""
    min_ats_score: float = 60.0
    max_results: int = 25
    greenhouse_boards: Optional[List[str]] = None
    lever_companies: Optional[List[str]] = None

class TailorRequest(BaseModel):
    resume_id: str
    job_title: str
    company: str
    job_description: str
    job_url: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: int = 0):
    if _is_authenticated(request):
        return RedirectResponse("/", status_code=303)
    demo_email, _ = _app_credentials()
    demo_hint = f"{demo_email} / {os.getenv('APP_PASSWORD', 'resume123')}" if os.getenv("APP_DEMO_HINT") == "1" else None
    return templates.TemplateResponse(request, "login.html", {"request": request, "error": bool(error), "demo_hint": demo_hint})

@app.post("/login")
async def login_submit(email: str = Form(...), password: str = Form(...), remember: Optional[str] = Form(None)):
    token = secrets.token_urlsafe(32)
    _session_tokens.add(token)
    response = RedirectResponse("/", status_code=303)
    # "remember me" keeps the session for 30 days, otherwise it ends when the browser closes
    response.set_cookie(SESSION_COOKIE, token, max_age=60 * 60 * 24 * 30 if remember else None, httponly=True, samesite="lax")
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response

@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        resume_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{resume_id}_{file.filename}"
        
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        resume_text = await asyncio.to_thread(pdf_reader.extract_text, str(file_path))
        
        if not resume_text:
            raise HTTPException(status_code=400, detail="No text extracted from PDF")
        
        await asyncio.to_thread(rag_engine.add_document, resume_id, resume_text, {"filename": file.filename})
        _resume_text_cache[resume_id] = resume_text
        
        return JSONResponse({
            "success": True,
            "resume_id": resume_id,
            "filename": file.filename,
            "resume_text": resume_text[:500] + "..."
        })
        
    except Exception as e:
        logger.error(f"Error uploading resume: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-resume")
async def analyze_resume(
    resume_id: str = Form(...),
    job_description: str = Form(...)
):
    try:
        resume_text = rag_engine.get_document_text(resume_id)
        
        if not resume_text:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        resume_skills = await asyncio.to_thread(skill_extractor.extract_skills, resume_text)
        jd_skills = await asyncio.to_thread(skill_extractor.extract_skills, job_description)
        
        ats_result = await asyncio.to_thread(
            ats_calculator.calculate_score,
            resume_skills, jd_skills, resume_text, job_description
        )
        
        # Gemini calls are slow network operations - run them concurrently off the event loop
        summary, questions = await asyncio.gather(
            asyncio.to_thread(
                summary_generator.generate_summary,
                resume_text, job_description, resume_skills, jd_skills
            ),
            asyncio.to_thread(
                interview_generator.generate_questions,
                resume_text, job_description, resume_skills, jd_skills
            ),
        )
        
        suggestions = await asyncio.to_thread(
            ats_calculator.generate_suggestions,
            resume_skills, jd_skills, resume_text
        )
        
        return JSONResponse({
            "success": True,
            "resume_id": resume_id,
            "ats_score": ats_result["score"],
            "matched_skills": ats_result["matched_skills"],
            "missing_skills": ats_result["missing_skills"],
            "skill_percentage": ats_result["percentage"],
            "candidate_summary": summary,
            "interview_questions": questions,
            "improvement_suggestions": suggestions
        })
        
    except Exception as e:
        logger.error(f"Error analyzing resume: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag-chat")
async def rag_chat(request: ChatRequest):
    try:
        context = await asyncio.to_thread(rag_engine.query, request.question, request.resume_id)
        
        if not context:
            return JSONResponse({
                "answer": "I couldn't find specific information about that in the resume. Please ask about the candidate's experience, skills, or projects."
            })
        
        answer = await asyncio.to_thread(rag_engine.generate_answer, request.question, context)
        
        return JSONResponse({
            "question": request.question,
            "answer": answer,
            "context": context
        })
        
    except Exception as e:
        logger.error(f"Error in RAG chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/job-search")
async def job_search(request: JobSearchRequest):
    """
    Finds open job postings via public job-board APIs (RemoteOK, Adzuna,
    Greenhouse, Lever) and scores each one against the candidate's resume,
    returning only postings that meet the requested minimum ATS score
    ("eligible" jobs). This does NOT scrape LinkedIn/Indeed and does NOT
    submit any applications.
    """
    try:
        resume_text = rag_engine.get_document_text(request.resume_id) or _resume_text_cache.get(request.resume_id)
        if not resume_text:
            raise HTTPException(status_code=404, detail="Resume not found. Upload a resume first.")

        def _search_and_score() -> Dict:
            jobs = job_search_engine.search(
                keywords=request.keywords,
                location=request.location,
                max_results=request.max_results,
                greenhouse_boards=request.greenhouse_boards,
                lever_companies=request.lever_companies,
            )

            resume_skills = skill_extractor.extract_skills(resume_text)

            eligible_jobs = []
            for job in jobs:
                jd_skills = skill_extractor.extract_skills(job.get("description", ""))
                score_result = ats_calculator.calculate_score(
                    resume_skills, jd_skills, resume_text, job.get("description", "")
                )
                if score_result["score"] >= request.min_ats_score:
                    eligible_jobs.append({
                        **job,
                        "description": job.get("description", "")[:1200],  # trim for payload size
                        "ats_score": score_result["score"],
                        "matched_skills": score_result["matched_skills"],
                        "missing_skills": score_result["missing_skills"],
                    })

            eligible_jobs.sort(key=lambda j: j["ats_score"], reverse=True)
            return jobs, eligible_jobs

        jobs, eligible_jobs = await asyncio.to_thread(_search_and_score)

        return JSONResponse({
            "success": True,
            "total_found": len(jobs),
            "eligible_count": len(eligible_jobs),
            "jobs": eligible_jobs,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tailor-resume")
async def tailor_resume(request: TailorRequest):
    """
    Generates a tailored resume + cover letter for one specific job, and
    saves downloadable .docx files. Nothing is submitted anywhere — the
    candidate reviews and downloads the materials, then applies themselves
    (optionally via the job_url returned by /api/job-search).
    """
    try:
        resume_text = rag_engine.get_document_text(request.resume_id) or _resume_text_cache.get(request.resume_id)
        if not resume_text:
            raise HTTPException(status_code=404, detail="Resume not found. Upload a resume first.")

        result = await asyncio.to_thread(
            resume_tailor.tailor,
            resume_text=resume_text,
            job_title=request.job_title,
            company=request.company,
            job_description=request.job_description,
        )

        tailor_id = str(uuid.uuid4())
        resume_out = TAILORED_DIR / f"{tailor_id}_resume.docx"
        cover_out = TAILORED_DIR / f"{tailor_id}_cover_letter.docx"

        ResumeBuilder.build_tailored_resume(
            candidate_name="Candidate",
            original_resume_text=resume_text,
            tailored=result["tailored_resume"],
            output_path=resume_out,
        )
        ResumeBuilder.build_cover_letter(
            cover_letter_text=result["cover_letter"],
            output_path=cover_out,
        )

        _tailored_cache[tailor_id] = {
            "resume_path": str(resume_out),
            "cover_letter_path": str(cover_out),
            "job_url": request.job_url,
        }

        return JSONResponse({
            "success": True,
            "tailor_id": tailor_id,
            "job_title": result["job_title"],
            "company": result["company"],
            "before_ats_score": result["before_score"]["score"],
            "after_ats_score": result["after_score"]["score"],
            "tailored_resume": result["tailored_resume"],
            "cover_letter": result["cover_letter"],
            "resume_download_url": f"/api/download-tailored/{tailor_id}/resume",
            "cover_letter_download_url": f"/api/download-tailored/{tailor_id}/cover-letter",
            "job_url": request.job_url,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tailoring resume: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download-tailored/{tailor_id}/{doc_type}")
async def download_tailored(tailor_id: str, doc_type: str):
    entry = _tailored_cache.get(tailor_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Tailored document not found")

    if doc_type == "resume":
        path = entry["resume_path"]
        filename = "tailored_resume.docx"
    elif doc_type == "cover-letter":
        path = entry["cover_letter_path"]
        filename = "cover_letter.docx"
    else:
        raise HTTPException(status_code=400, detail="doc_type must be 'resume' or 'cover-letter'")

    if not Path(path).exists():
        raise HTTPException(status_code=404, detail="File no longer available")

    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "AI Resume Assistant is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
