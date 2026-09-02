"""Generate interview questions for a candidate using the Gemini AI model.

Takes the candidate's resume text, a target job description, and extracted
skill lists, and produces a structured set of technical, behavioral, and
scenario-based interview questions. Falls back to deterministic template
questions when the Gemini API key is missing or the call fails, so the
feature never hard-crashes.
"""

import os
import google.generativeai as genai
from typing import List, Dict
import logging
import json

logger = logging.getLogger(__name__)

class InterviewGenerator:
    """Generate interview questions using Gemini AI"""
    
    GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT", "120"))

    def __init__(self):
        self.model = None
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found")
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-3.6-flash"))
    
    def generate_questions(
        self,
        resume_text: str,
        job_description: str,
        resume_skills: List[str],
        jd_skills: List[str]
    ) -> Dict:
        try:
            if self.model is None:
                logger.warning("Gemini model unavailable; using fallback questions")
                return self._fallback_questions(resume_skills, jd_skills)

            resume_preview = resume_text[:2000] if len(resume_text) > 2000 else resume_text
            jd_preview = job_description[:1000] if len(job_description) > 1000 else job_description
            
            prompt = f"""
            Generate interview questions for a candidate based on their resume and the job description:
            
            Resume:
            {resume_preview}
            
            Job Description:
            {jd_preview}
            
            Skills: {', '.join(resume_skills[:10])}
            Required Skills: {', '.join(jd_skills[:10])}
            
            Generate 20 questions in JSON format:
            1. technical_questions: 10 technical questions
            2. behavioral_questions: 5 behavioral questions
            3. scenario_questions: 5 scenario-based questions
            
            Make questions specific to the candidate's experience and the role requirements.
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
                    questions = json.loads(json_str)
                else:
                    questions = self._fallback_questions(resume_skills, jd_skills)
            except:
                questions = self._fallback_questions(resume_skills, jd_skills)
            
            default = self._fallback_questions([], [])
            for key in default:
                if key not in questions:
                    questions[key] = default[key]
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            return self._fallback_questions(resume_skills, jd_skills)
    
    def _fallback_questions(self, resume_skills: List[str], jd_skills: List[str]) -> Dict:
        tech_skills = jd_skills[:5] if jd_skills else resume_skills[:5]
        
        technical_qs = [
            f"Explain your experience with {skill}?" for skill in tech_skills
        ]
        technical_qs.extend([
            "How do you approach debugging complex issues?",
            "Explain a time you optimized a system's performance.",
            "How do you ensure code quality and testing?",
            "Describe your experience with version control.",
            "How do you stay updated with new technologies?"
        ])
        
        behavioral_qs = [
            "Tell me about a time you faced a challenging project.",
            "How do you handle conflicts in a team?",
            "Describe your leadership experience.",
            "How do you prioritize tasks?",
            "Tell me about a time you failed and what you learned."
        ]
        
        scenario_qs = [
            "How would you handle a tight deadline?",
            "How would you handle a disagreement with a team member?",
            "How would you explain a technical concept to a non-technical stakeholder?",
            "How would you approach learning a new technology?",
            "How would you handle a production outage?"
        ]
        
        return {
            "technical_questions": technical_qs[:10],
            "behavioral_questions": behavioral_qs[:5],
            "scenario_questions": scenario_qs[:5]
        }