"""Tailor an existing resume to maximize ATS keyword match for a target job.

Rewrites/reorders the candidate's *real* experience (emphasis, keyword
phrasing, ordering, summary framing) to better fit a specific job description.
It is explicitly instructed NOT to invent employers, titles, dates, degrees,
or skills not supported by the source resume, keeping the output honest.
Scores the resume before and after tailoring using ATSScoreCalculator.
"""

import os
import json
import logging
from typing import Dict, List
import google.generativeai as genai

from utils.skill_extractor import SkillExtractor
from utils.ats_score import ATSScoreCalculator

logger = logging.getLogger(__name__)


class ResumeTailor:
    """
    Rewrites/reorders an existing resume's wording to better match a specific
    job description and maximize ATS keyword coverage.

    IMPORTANT: This tailors *presentation* of the candidate's real experience
    (emphasis, keyword phrasing, ordering, summary framing). It is instructed
    NOT to invent employers, titles, dates, degrees, or skills the candidate
    doesn't already have evidence of in the source resume. This keeps the
    output honest and reduces the risk of an easily-caught fabricated resume.
    """

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        if not api_key:
            logger.warning("GEMINI_API_KEY not found in environment variables")
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-3.6-flash"))

        self.skill_extractor = SkillExtractor()
        self.ats_calculator = ATSScoreCalculator()

    def tailor(self, resume_text: str, job_title: str, company: str, job_description: str) -> Dict:
        resume_skills = self.skill_extractor.extract_skills(resume_text)
        jd_skills = self.skill_extractor.extract_skills(job_description)

        before_score = self.ats_calculator.calculate_score(
            resume_skills, jd_skills, resume_text, job_description
        )

        tailored = self._generate_tailored_content(
            resume_text, job_title, company, job_description, jd_skills
        )

        tailored_text_for_scoring = self._flatten_for_scoring(tailored)
        tailored_skills = self.skill_extractor.extract_skills(tailored_text_for_scoring)
        after_score = self.ats_calculator.calculate_score(
            tailored_skills, jd_skills, tailored_text_for_scoring, job_description
        )

        return {
            "job_title": job_title,
            "company": company,
            "tailored_resume": tailored,
            "cover_letter": tailored.get("cover_letter", ""),
            "before_score": before_score,
            "after_score": after_score,
        }

    def _generate_tailored_content(
        self, resume_text: str, job_title: str, company: str, job_description: str, jd_skills: List[str]
    ) -> Dict:
        fallback = self._fallback_tailor(resume_text, job_title, company)

        if not self.model:
            return fallback

        resume_preview = resume_text[:6000]
        jd_preview = job_description[:2500]

        prompt = f"""
        You are helping a job candidate tailor their EXISTING resume for a specific job,
        to improve ATS (Applicant Tracking System) keyword match.

        Rules you MUST follow:
        - Do NOT invent new employers, job titles, dates, degrees, or certifications.
        - Do NOT claim skills or tools that have no support anywhere in the original resume.
        - You MAY rephrase, reorder, and re-emphasize real experience using terminology
          and keywords from the job description, where truthfully applicable.
        - You MAY tighten bullet points to be more quantifiable and achievement-focused,
          but only using details present in or reasonably inferable from the original resume.
        - Keep it truthful. This is about better presentation, not fabrication.

        Original resume:
        {resume_preview}

        Target job title: {job_title}
        Target company: {company}
        Job description:
        {jd_preview}

        Key skills/keywords from the job description: {', '.join(jd_skills[:20])}

        Return ONLY valid JSON with this exact shape (no markdown fences, no commentary):
        {{
          "professional_summary": "2-4 sentence summary tailored to this role",
          "highlighted_skills": ["skill1", "skill2", ...],
          "tailored_experience_bullets": ["rewritten bullet 1", "rewritten bullet 2", ...],
          "keywords_incorporated": ["keyword1", "keyword2", ...],
          "honesty_notes": "brief note on anything the candidate should verify/add before submitting",
          "cover_letter": "a short 3-paragraph cover letter for this specific role and company"
        }}
        """

        try:
            response = self.model.generate_content(
                prompt,
                request_options={"timeout": int(os.getenv("GEMINI_TIMEOUT", "120"))},
            )
            text = response.text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start == -1 or end == -1:
                return fallback
            data = json.loads(text[start:end])
            for key in fallback:
                data.setdefault(key, fallback[key])
            return data
        except Exception as e:
            logger.error(f"Error tailoring resume with Gemini: {e}")
            return fallback

    @staticmethod
    def _flatten_for_scoring(tailored: Dict) -> str:
        parts = [
            tailored.get("professional_summary", ""),
            " ".join(tailored.get("highlighted_skills", [])),
            " ".join(tailored.get("tailored_experience_bullets", [])),
        ]
        return " ".join(parts)

    @staticmethod
    def _fallback_tailor(resume_text: str, job_title: str, company: str) -> Dict:
        return {
            "professional_summary": f"Experienced professional pursuing the {job_title} role at {company}.",
            "highlighted_skills": [],
            "tailored_experience_bullets": [],
            "keywords_incorporated": [],
            "honesty_notes": "AI tailoring unavailable (missing GEMINI_API_KEY) — showing original resume content only.",
            "cover_letter": (
                f"Dear Hiring Manager,\n\nI am excited to apply for the {job_title} position at {company}. "
                f"My background aligns with this role and I would welcome the opportunity to discuss further.\n\n"
                f"Sincerely,\nCandidate"
            ),
        }
