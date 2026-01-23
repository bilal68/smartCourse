"""RAG API endpoints supporting OpenAI/Groq/Anthropic providers."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.db.session import get_db
from app.modules.rag.service import RAGService


# Request/Response models
class RAGRequest(BaseModel):
    question: str
    course_ids: Optional[List[str]] = None
    mode: str = "student"  # "student" or "instructor"
    provider: str = "groq"  # "groq", "openai", "anthropic"
    model_name: Optional[str] = None


class RAGResponse(BaseModel):
    question: str
    answer: str
    sources: List[dict]
    confidence: float
    mode: str
    model_info: dict
    error: Optional[str] = None


router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/ask", response_model=RAGResponse)
def ask_question(
    request: RAGRequest,
    db: Session = Depends(get_db)
):
    """
    Ask a question using RAG with cloud LLM providers.
    
    Supported providers:
    - **groq**: FREE tier (14,400 requests/day) - RECOMMENDED
    - **openai**: GPT models (paid)
    - **anthropic**: Claude models (paid)
    
    Modes:
    - **student**: Educational answers for learners
    - **instructor**: Pedagogical guidance for teachers
    """
    try:
        rag_service = RAGService(db)
        
        result = rag_service.ask_question(
            question=request.question,
            course_ids=request.course_ids,
            mode=request.mode,
            provider=request.provider,
            model_name=request.model_name
        )
        
        return RAGResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"RAG service error: {str(e)}"
        )


@router.get("/providers")
def get_available_providers():
    """Get list of supported LLM providers and their models."""
    return {
        "providers": {
            "groq": {
                "name": "Groq",
                "type": "cloud_api",
                "cost": "FREE (14,400 requests/day)",
                "models": [
                    "llama-3.1-8b-instant",
                    "llama-3.1-70b-versatile", 
                    "mixtral-8x7b-32768",
                    "gemma-7b-it"
                ],
                "setup": "Get free API key from https://console.groq.com",
                "env_var": "GROQ_API_KEY"
            },
            "openai": {
                "name": "OpenAI",
                "type": "cloud_api", 
                "cost": "PAID (~$0.001-0.002 per 1K tokens)",
                "models": [
                    "gpt-3.5-turbo",
                    "gpt-4",
                    "gpt-4-turbo"
                ],
                "setup": "Get API key from https://platform.openai.com",
                "env_var": "OPENAI_API_KEY"
            },
            "anthropic": {
                "name": "Anthropic Claude",
                "type": "cloud_api",
                "cost": "PAID (~$0.0008-0.024 per 1K tokens)",
                "models": [
                    "claude-3-haiku-20240307",
                    "claude-3-sonnet-20240229",
                    "claude-3-5-sonnet-20241022"
                ],
                "setup": "Get API key from https://console.anthropic.com",
                "env_var": "ANTHROPIC_API_KEY"
            }
        },
        "recommendation": "Use Groq for free tier with excellent performance"
    }


@router.get("/health")
def health_check():
    """Health check endpoint for RAG service."""
    return {
        "status": "healthy",
        "service": "RAG with cloud LLM providers",
        "supported_providers": ["groq", "openai", "anthropic"]
    }