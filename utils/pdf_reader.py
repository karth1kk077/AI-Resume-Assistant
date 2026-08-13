import fitz
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class PDFReader:
    """Extract text from PDF files"""
    
    @staticmethod
    def extract_text(pdf_path: str) -> Optional[str]:
        try:
            text = ""
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    text += page.get_text()
            
            text = " ".join(text.split())
            
            if not text.strip():
                logger.warning(f"No text extracted from {pdf_path}")
                return None
                
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return None