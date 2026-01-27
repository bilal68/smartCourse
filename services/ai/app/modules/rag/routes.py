"""RAG API endpoints supporting OpenAI/Groq/Anthropic providers."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import json

from app.db.session import get_db
from app.modules.rag.service import RAGService


# Request/Response models
class RAGRequest(BaseModel):
    question: str
    course_ids: Optional[List[str]] = None
    mode: str = "student"  # "student" or "instructor"
    provider: str = "groq"  # "groq", "openai", "anthropic"
    model_name: Optional[str] = None


router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/ask/stream")
def ask_question_stream(
    request: RAGRequest,
    db: Session = Depends(get_db)
):
    """
    Ask a question using RAG with streaming response from cloud LLM providers.
    
    Returns Server-Sent Events (SSE) for real-time streaming responses.
    
    Supported providers:
    - **groq**: FREE tier (14,400 requests/day) - RECOMMENDED
    - **openai**: GPT models (paid)
    - **anthropic**: Claude models (paid)
    
    Modes:
    - **student**: Educational answers for learners
    - **instructor**: Pedagogical guidance for teachers
    
    Response format: Server-Sent Events with JSON data chunks
    """
    try:
        def generate_stream():
            rag_service = RAGService(db)
            
            for chunk in rag_service.ask_question_stream(
                question=request.question,
                course_ids=request.course_ids,
                mode=request.mode,
                provider=request.provider,
                model_name=request.model_name
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"RAG streaming service error: {str(e)}"
        )


@router.get("/health")
def health_check():
    """Health check endpoint for RAG service."""
    return {
        "status": "healthy",
        "service": "RAG with cloud LLM providers",
        "supported_providers": ["groq", "openai", "anthropic"]
    }