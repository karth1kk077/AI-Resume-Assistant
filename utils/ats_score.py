from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)

class ATSScoreCalculator:
    """Calculate ATS compatibility score"""
    
    @staticmethod
    def calculate_score(
        resume_skills: List[str],
        jd_skills: List[str],
        resume_text: str,
        job_description: str
    ) -> Dict:
        try:
            resume_skills_set = set(resume_skills)
            jd_skills_set = set(jd_skills)
            
            matched_skills = resume_skills_set.intersection(jd_skills_set)
            missing_skills = jd_skills_set - resume_skills_set
            
            total_jd_skills = len(jd_skills_set)
            matched_count = len(matched_skills)
            
            if total_jd_skills == 0:
                percentage = 0
            else:
                percentage = (matched_count / total_jd_skills) * 100
            
            experience_keywords = ['experience', 'years', 'senior', 'lead', 'manager']
            has_experience = any(keyword in resume_text.lower() for keyword in experience_keywords)
            
            education_keywords = ['bachelor', 'master', 'phd', 'degree', 'university', 'college']
            has_education = any(keyword in resume_text.lower() for keyword in education_keywords)
            
            achievement_indicators = ['achieved', 'led', 'improved', 'increased', 'reduced', 'saved']
            has_achievements = any(indicator in resume_text.lower() for indicator in achievement_indicators)
            
            bonus_points = 0
            if has_experience:
                bonus_points += 5
            if has_education:
                bonus_points += 5
            if has_achievements:
                bonus_points += 5
            
            final_score = min(percentage + bonus_points, 100)
            
            recommendations = []
            
            if missing_skills:
                recommendations.append(f"Add {len(missing_skills)} missing skills: {', '.join(list(missing_skills)[:5])}")
            
            if percentage < 50:
                recommendations.append("Significant skill gaps detected. Consider adding more relevant technologies.")
            
            if not has_experience:
                recommendations.append("Add detailed work experience with specific years and achievements.")
            
            if not has_education:
                recommendations.append("Include educational qualifications and certifications.")
            
            if not has_achievements:
                recommendations.append("Add quantifiable achievements and metrics in your experience section.")
            
            return {
                "score": round(final_score, 1),
                "percentage": round(percentage, 1),
                "matched_skills": sorted(list(matched_skills)),
                "missing_skills": sorted(list(missing_skills)),
                "bonus_points": bonus_points,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Error calculating ATS score: {str(e)}")
            return {
                "score": 0,
                "percentage": 0,
                "matched_skills": [],
                "missing_skills": [],
                "bonus_points": 0,
                "recommendations": ["Error in score calculation"]
            }
    
    @staticmethod
    def generate_suggestions(
        resume_skills: List[str],
        jd_skills: List[str],
        resume_text: str
    ) -> List[str]:
        suggestions = []
        
        missing = set(jd_skills) - set(resume_skills)
        if missing:
            suggestions.append(f"Add these missing skills: {', '.join(list(missing)[:7])}")
        
        if len(resume_skills) < 5:
            suggestions.append("Add more technical skills to increase ATS compatibility")
        
        if len(resume_text.split()) < 200:
            suggestions.append("Consider expanding your resume with more details about experience and projects")
        
        for skill in jd_skills[:10]:
            if skill.lower() not in resume_text.lower():
                suggestions.append(f"Consider mentioning '{skill}' in your experience or projects")
        
        return suggestions[:5]