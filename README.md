# 🤖 AI Resume Screening & Interview Assistant

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Gemini-API-orange.svg)](https://ai.google.dev/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3.0-yellow.svg)](https://www.langchain.com/)
[![License](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)

> 🚀 A production-ready AI-powered resume screening and interview assistant built with Python, FastAPI, NLP, and Google Gemini API.

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
- **Context-Aware Responses** using vector embeddings
- **Project & Experience Queries** - "What projects has the candidate worked on?"
- **Skill Verification** - "Does the candidate know FastAPI?"
- **Strictly from documents** - No hallucination

### 🎨 Modern Dashboard
- Clean, responsive UI with real-time updates
- Interactive ATS score visualization
- Tabbed interview questions view
- Embedded AI chat interface

## 🛠️ Tech Stack

### Backend
- **Python 3.12** - Core programming language
- **FastAPI** - High-performance web framework
- **Google Gemini API** - LLM for summary and question generation
- **LangChain** - Framework for LLM applications
- **FAISS** - Vector search for RAG
- **Sentence Transformers** - Embedding generation
- **PyMuPDF** - PDF text extraction

### Frontend
- **HTML/CSS/JavaScript** - Clean, responsive design
- **Jinja2 Templates** - Server-side rendering

## 📦 Installation

### Prerequisites
- Python 3.12+
- Google Gemini API Key ([Get it here](https://aistudio.google.com/app/apikey))

### Step 1: Clone the Repository

```bash
git clone https://github.com/umerafzalkhan/AI-Resume-Assistant.git
cd AI-Resume-Assistant