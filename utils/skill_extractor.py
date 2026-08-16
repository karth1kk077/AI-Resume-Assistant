import re
import logging
from typing import List

logger = logging.getLogger(__name__)

class SkillExtractor:
    """Extract technical skills from text"""
    
    SKILLS = {
        "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go", "rust",
        "swift", "kotlin", "php", "html", "css", "sql", "nosql", "r", "scala",
        "react", "angular", "vue", "node", "django", "flask", "spring", "fastapi",
        "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "matplotlib",
        "seaborn", "plotly", "dash", "streamlit", "gradio",
        "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "cassandra",
        "dynamodb", "firebase", "sqlite", "oracle", "mssql",
        "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "git", "github",
        "gitlab", "bitbucket", "terraform", "ansible", "chef", "puppet",
        "machine learning", "deep learning", "nlp", "computer vision", "neural networks",
        "llm", "gpt", "gemini", "bert", "transformers", "rag", "langchain",
        "jira", "confluence", "slack", "microsoft office", "excel", "power bi",
        "tableau", "looker", "airflow", "kafka", "rabbitmq", "nginx", "apache",
        "agile", "scrum", "kanban", "devops", "ci/cd", "tdd", "bdd", "microservices",
        "rest api", "graphql", "soap", "grpc", "websocket"
    }
    
    @staticmethod
    def extract_skills(text: str) -> List[str]:
        try:
            text_lower = text.lower()
            found_skills = set()
            
            for skill in SkillExtractor.SKILLS:
                if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
                    found_skills.add(skill)
            
            patterns = [
                r'(?:experience|knowledge|proficient|familiar|expertise) with\s+([\w\s]+)',
                r'skills?:?\s*([\w\s,]+)',
                r'technologies?:?\s*([\w\s,]+)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                for match in matches:
                    skills = re.split(r'[,;]\s*', match)
                    for skill in skills:
                        skill_clean = skill.strip()
                        if len(skill_clean) > 2 and len(skill_clean) < 30:
                            if re.search(r'[a-zA-Z]', skill_clean):
                                found_skills.add(skill_clean.lower())
            
            return sorted(list(found_skills))
            
        except Exception as e:
            logger.error(f"Error extracting skills: {str(e)}")
            return []