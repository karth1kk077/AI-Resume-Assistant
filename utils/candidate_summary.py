import os
import google.generativeai as genai
from typing import Dict, List
import logging
import json

logger = logging.getLogger(__name__)

class CandidateSummaryGenerator:
    """Generate candidate summaries using Gemini AI"""
    
    GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT", "120"))

    def __init__(self):
        self.model = None
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found in environment variables")
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-3.6-flash"))
    
    def generate_summary(
        self,
        resume_text: str,
        job_description: str,
        resume_skills: List[str],
        jd_skills: List[str]
    ) -> Dict:
        try:
            if self.model is None:
                logger.warning("Gemini model unavailable; using fallback summary")
                return self._fallback_summary(resume_text, resume_skills)

            resume_preview = resume_text[:3000] if len(resume_text) > 3000 else resume_text
            jd_preview = job_description[:1000] if len(job_description) > 1000 else job_description
            
            prompt = f"""
            Analyze the following resume and job description. Provide a comprehensive candidate summary:
            
            Resume:
            {resume_preview}
            
            Job Description:
            {jd_preview}
            
            Resume Skills: {', '.join(resume_skills[:15])}
            Required Skills: {', '.join(jd_skills[:15])}
            
            Please provide the following in JSON format:
            1. professional_summary: A 2-3 sentence professional summary
            2. experience_summary: Summary of experience and key achievements
            3. key_technical_skills: Key technical skills (list)
            4. strengths: Top strengths (list)
            5. weaknesses: Areas for improvement (list)
            6. hiring_recommendation: Recommend or Not Recommended with reason
            
            Format as JSON.
            """
            
            response = self.model.generate_content(
                prompt,
                request_options={"timeout": self.GEMINI_TIMEOUT_SECONDS},
            )
            response_text = response.text
            
            try:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start != -1 and end != -1:
                    json_str = response_text[start:end]
                    summary_data = json.loads(json_str)
                else:
                    summary_data = self._fallback_summary(resume_text, resume_skills)
            except:
                summary_data = self._fallback_summary(resume_text, resume_skills)
            
            return summary_data
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return self._fallback_summary(resume_text, resume_skills)
    
    def _fallback_summary(self, resume_text: str, skills: List[str]) -> Dict:
        return {
            "professional_summary": "Candidate with relevant experience and skills",
            "experience_summary": "Experience details extracted from resume",
            "key_technical_skills": skills[:10] if skills else [],
            "strengths": ["Technical skills", "Experience"],
            "weaknesses": ["Consider adding more details"],
            "hiring_recommendation": "Recommended"
        }