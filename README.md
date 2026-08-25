# 🤖 AI Resume Screening & Interview Assistant

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Gemini-API-orange.svg)](https://ai.google.dev/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3.0-yellow.svg)](https://www.langchain.com/)
[![License](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)

> 🚀 An AI-powered resume screening, job matching, and interview assistant built with Python, FastAPI, NLP, FAISS, and the Google Gemini API.

Upload a resume, paste a job description, and get an instant ATS score, an AI-generated candidate summary, tailored interview questions, eligible job matches from public job boards, and a downloadable tailored resume + cover letter.

## 📌 Features

### 📄 Resume Upload & Processing
- Upload PDF resumes with drag-and-drop support
- Automatic text extraction using PyMuPDF
- Support for multi-page resumes

### 🔍 ATS Score Calculator
- **Skill Match Percentage** - Compare resume skills with job requirements
- **Matched Skills** - Identify skills that align with the job
- **Missing Skills** - Highlight gaps for improvement
- **ATS Score** - Get a compatibility score out of 100
- **Smart Recommendations** - Actionable suggestions for resume optimization

### 👤 AI-Powered Candidate Summary
- **Professional Summary** - AI-generated overview of the candidate
- **Experience Summary** - Key achievements and experience highlights
- **Key Technical Skills** - Extracted and ranked skills
- **Strengths & Weaknesses** - AI-analyzed candidate profile
- **Hiring Recommendation** - AI-driven hiring decision support

### 🎤 Smart Interview Question Generator
- **10 Technical Questions** - Role-specific technical assessment
- **5 Behavioral Questions** - Soft skills and cultural fit evaluation
- **5 Scenario-Based Questions** - Real-world problem-solving scenarios
- Questions are **tailored** to the candidate's resume and job description

### 💬 RAG-Powered Chat Assistant
- **Ask Questions** about the candidate's resume
- **Context-Aware Responses** using FAISS vector embeddings
- **Project & Experience Queries** - "What projects has the candidate worked on?"
- **Skill Verification** - "Does the candidate know FastAPI?"
- **Strictly from documents** - No hallucination

### 🎯 Job Search & ATS Filtering
- Searches live job postings from **public, ToS-compliant sources**:
  - [RemoteOK](https://remoteok.com/api) - no API key required
  - [Adzuna](https://developer.adzuna.com/) - free API key required
  - [Greenhouse](https://boards-api.greenhouse.io/v1/boards) job boards - no key, needs board tokens
  - [Lever](https://api.lever.co/v0/postings) job boards - no key, needs company slugs
- Every posting is **scored against the candidate's resume** using the ATS calculator
- Only jobs meeting a configurable minimum ATS score ("eligible" jobs) are returned, sorted by fit
- Does **not** scrape LinkedIn/Indeed and does **not** auto-submit applications

### 📝 Resume Tailoring & Cover Letter Builder
- Rewrites/reorders the candidate's **real** experience to maximize ATS keyword match for one specific job
- **Honesty-first**: never invents employers, titles, dates, degrees, or skills
- Shows **before/after ATS scores** so you can see the improvement
- Generates a tailored **cover letter** for the specific role and company
- Downloads the results as ready-to-apply **`.docx` files**
- Nothing is submitted anywhere - you review and apply yourself

### 🎨 Modern Dashboard
- Clean, responsive UI with real-time updates
- Interactive ATS score visualization
- Tabbed interview questions view (Technical / Behavioral / Scenario)
- Embedded AI chat interface
- Job search & tailoring workspace

## 🛠️ Tech Stack

### Backend
- **Python 3.12** - Core programming language
- **FastAPI** - High-performance web framework
- **Google Gemini API** - LLM for summaries, questions, tailoring, and chat answers
- **LangChain** - Framework for LLM applications
- **FAISS** - Vector search for RAG
- **Sentence Transformers** - Embedding generation
- **PyMuPDF** - PDF text extraction
- **python-docx** - Tailored resume / cover letter generation (.docx)
- **Requests** - Job board API clients

### Frontend
- **HTML/CSS/JavaScript** - Clean, responsive design
- **Jinja2 Templates** - Server-side rendering

## 📦 Installation

### Prerequisites
- Python 3.12+
- Google Gemini API Key ([Get it here](https://aistudio.google.com/app/apikey))

### Step 1: Clone the Repository

```bash
git clone karth1kk077/AI-Resume-Assistant
cd AI-Resume-Assistant
```

### Step 2: Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it:

- **Windows (PowerShell):**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt):**
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

```bash
cp .env.example .env
```

Then edit `.env`:

```env
GEMINI_API_KEY=your_gemini_key_here

# Optional - enables the Adzuna job source (RemoteOK works with no key)
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
```

> 💡 The app runs without `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` - RemoteOK still works. Only the Adzuna job source is disabled.

### Step 5: Run the Application

```bash
python app.py
```

Open your browser and go to **http://localhost:8000**

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Dashboard UI |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/upload-resume` | Upload a PDF resume, returns a `resume_id` |
| `POST` | `/api/analyze-resume` | ATS score, candidate summary & interview questions for a job description |
| `POST` | `/api/rag-chat` | Ask questions about the uploaded resume (RAG) |
| `POST` | `/api/job-search` | Find eligible jobs matching the resume, scored by ATS |
| `POST` | `/api/tailor-resume` | Generate a tailored resume + cover letter for one job |
| `GET` | `/api/download-tailored/{tailor_id}/{doc_type}` | Download the tailored `.docx` (doc_type: `resume` or `cover-letter`) |

## 📂 Project Structure

```
├── app.py                  # FastAPI application & routes
├── requirements.txt
├── .env.example
├── templates/
│   └── index.html          # Dashboard UI
├── static/
│   ├── app.js              # Frontend logic
│   └── style.css
├── utils/
│   ├── pdf_reader.py       # PDF text extraction
│   ├── skill_extractor.py  # Skills / keyword extraction
│   ├── ats_score.py        # ATS score calculator
│   ├── candidate_summary.py# Gemini candidate summary
│   ├── interview_generator.py # Interview question generation
│   ├── rag_engine.py       # FAISS vector store + chat answers
│   ├── job_search.py       # RemoteOK / Adzuna / Greenhouse / Lever clients
│   ├── resume_tailor.py    # ATS keyword tailoring via Gemini
│   └── resume_builder.py   # .docx generation for resume & cover letter
├── uploads/                # Uploaded resumes (created at runtime)
├── tailored_output/        # Generated .docx files (created at runtime)
├── faiss_db/               # Vector index (created at runtime)
└── screenshots/
```

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

[MIT](LICENSE)
