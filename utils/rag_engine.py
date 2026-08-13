import os
import logging
import pickle
import re
from pathlib import Path
from typing import Dict, List, Optional

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    import faiss
except Exception as e:
    np = None
    SentenceTransformer = None
    faiss = None
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.warning(f"RAG dependencies unavailable: {e}")
else:
    logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
except ImportError:
    genai = None
    logger.warning("google.generativeai is not installed; RAG answer generation is disabled")

class RAGEngine:
    """RAG engine using FAISS for vector search"""
    
    def __init__(self, persist_path: str = "./faiss_db"):
        self.embedder = None
        self.rag_enabled = False
        self.raw_documents = {}
        self.model = None

        api_key = os.getenv("GEMINI_API_KEY")
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        if api_key and genai is not None:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(model_name)
            except Exception as e:
                logger.warning(f"Gemini API initialization failed: {e}")
                self.model = None
        else:
            if api_key is None:
                logger.warning("GEMINI_API_KEY not found")
            self.model = None

        if SentenceTransformer is not None and faiss is not None:
            try:
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
                self.rag_enabled = True
            except Exception as e:
                logger.warning(f"SentenceTransformer initialization failed: {e}")
                self.embedder = None
        else:
            logger.warning("RAG engine disabled due to missing dependencies")

        self.persist_path = Path(persist_path)
        self.persist_path.mkdir(exist_ok=True)

        self.index = None
        self.documents = []
        self.metadata = []
        self.doc_id_map = {}

        if self.rag_enabled:
            self._load_index()
    
    def add_document(self, doc_id: str, text: str, metadata: Dict = None):
        self.raw_documents[doc_id] = text

        if not self.rag_enabled:
            logger.warning(f"Skipping RAG vectorization for document {doc_id} because RAG engine is disabled; using text fallback for chat")
            return

        try:
            chunks = self._chunk_text(text, chunk_size=500, overlap=100)
            
            if not chunks:
                logger.warning(f"No chunks generated for document {doc_id}")
                return
            
            embeddings = self.embedder.encode(chunks)
            
            if self.index is None:
                dimension = embeddings.shape[1]
                self.index = faiss.IndexFlatL2(dimension)
            
            self.index.add(embeddings.astype('float32'))
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_{i}"
                self.documents.append(chunk)
                self.doc_id_map[chunk_id] = doc_id
                self.metadata.append({
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    **(metadata or {})
                })
            
            self._save_index()
            logger.info(f"Added document {doc_id} with {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error adding document: {str(e)}")
            raise
    
    def query(self, question: str, doc_id: str, top_k: int = 3) -> str:
        try:
            if doc_id not in self.raw_documents:
                return ""

            document_text = self.raw_documents[doc_id]
            if not document_text:
                return ""

            if self.rag_enabled and self.index is not None and len(self.documents) > 0:
                doc_indices = []
                for i, meta in enumerate(self.metadata):
                    if meta.get("doc_id") == doc_id:
                        doc_indices.append(i)

                if not doc_indices:
                    logger.warning(f"No documents found for doc_id {doc_id}")
                    return self._fallback_query(question, document_text, top_k)

                doc_embeddings = []
                doc_texts = []
                for idx in doc_indices:
                    chunk_text = self.documents[idx]
                    embedding = self.embedder.encode([chunk_text])[0]
                    doc_embeddings.append(embedding)
                    doc_texts.append(chunk_text)

                if not doc_embeddings:
                    return self._fallback_query(question, document_text, top_k)

                temp_index = faiss.IndexFlatL2(len(doc_embeddings[0]))
                temp_index.add(np.array(doc_embeddings).astype('float32'))

                query_embedding = self.embedder.encode([question])[0]
                distances, indices = temp_index.search(
                    query_embedding.reshape(1, -1).astype('float32'),
                    min(top_k, len(doc_embeddings))
                )

                relevant_chunks = [doc_texts[idx] for idx in indices[0]]
                context = "\n\n---\n\n".join(relevant_chunks)
                return context

            return self._fallback_query(question, document_text, top_k)

        except Exception as e:
            logger.error(f"Error querying RAG: {str(e)}")
            return ""
    
    def _fallback_query(self, question: str, document_text: str, top_k: int = 3) -> str:
        if not document_text:
            return ""

        normalized_question = re.findall(r"[a-z0-9]+", question.lower())
        chunks = self._chunk_text(document_text, chunk_size=300, overlap=80)

        if not chunks:
            return document_text[:2000]

        if not normalized_question:
            return "\n\n---\n\n".join(chunks[:top_k])

        scored_chunks = []
        for chunk in chunks:
            chunk_lower = chunk.lower()
            score = sum(1 for term in normalized_question if term in chunk_lower)
            if score > 0:
                scored_chunks.append((score, chunk))

        if not scored_chunks:
            return "\n\n---\n\n".join(chunks[:top_k])

        scored_chunks.sort(reverse=True)
        return "\n\n---\n\n".join(chunk for _, chunk in scored_chunks[:top_k])

    def generate_answer(self, question: str, context: str) -> str:
        try:
            if not self.model:
                if context:
                    return self._answer_from_context(question, context)
                return "I couldn't generate an answer because the Gemini model is unavailable and no resume context was found."
            
            prompt = f"""
            Based on the following context from a candidate's resume, answer the question.
            If the answer is not in the context, say so.
            
            Context:
            {context}
            
            Question: {question}
            
            Answer:
            """
            
            response = self.model.generate_content(
                prompt,
                request_options={"timeout": int(os.getenv("GEMINI_TIMEOUT", "120"))},
            )
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            if context:
                return self._answer_from_context(question, context)
            return f"Error generating answer: {str(e)}"
    
    def _answer_from_context(self, question: str, context: str) -> str:
        question_terms = re.findall(r"[a-z0-9]+", question.lower())
        if not question_terms:
            return "I couldn't understand that question clearly. Please ask about skills, experience, projects, or education."

        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', context) if s.strip()]
        if not sentences:
            return context[:2000]

        scored_sentences = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            score = sum(1 for term in question_terms if term in sentence_lower)
            if score > 0:
                scored_sentences.append((score, sentence))

        if scored_sentences:
            scored_sentences.sort(key=lambda item: (-item[0], len(item[1])))
            return scored_sentences[0][1][:500]

        return f"Based on the uploaded resume, the relevant information is: {context[:2000]}"

    def get_document_text(self, doc_id: str) -> str:
        try:
            if doc_id in self.raw_documents:
                return self.raw_documents[doc_id]

            chunks = []
            for i, meta in enumerate(self.metadata):
                if meta.get("doc_id") == doc_id:
                    chunks.append(self.documents[i])
            return " ".join(chunks)
        except Exception as e:
            logger.error(f"Error getting document: {str(e)}")
            return ""
    
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def _save_index(self):
        try:
            if self.index is not None:
                faiss.write_index(self.index, str(self.persist_path / "index.faiss"))
                
            with open(self.persist_path / "metadata.pkl", 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'metadata': self.metadata,
                    'doc_id_map': self.doc_id_map
                }, f)
                
            logger.info("Index saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving index: {str(e)}")
    
    def _load_index(self):
        try:
            index_path = self.persist_path / "index.faiss"
            metadata_path = self.persist_path / "metadata.pkl"
            
            if index_path.exists():
                self.index = faiss.read_index(str(index_path))
                
            if metadata_path.exists():
                with open(metadata_path, 'rb') as f:
                    data = pickle.load(f)
                    self.documents = data.get('documents', [])
                    self.metadata = data.get('metadata', [])
                    self.doc_id_map = data.get('doc_id_map', {})
                    
                logger.info(f"Loaded index with {len(self.documents)} chunks")
                
        except Exception as e:
            logger.warning(f"Could not load index: {str(e)}")
            self.index = None
            self.documents = []
            self.metadata = []
            self.doc_id_map = {}
    
    def reset(self):
        self.index = None
        self.documents = []
        self.metadata = []
        self.doc_id_map = {}
        
        try:
            for file in self.persist_path.glob("*"):
                file.unlink()
            logger.info("RAG system reset successfully")
        except Exception as e:
            logger.error(f"Error resetting: {str(e)}")