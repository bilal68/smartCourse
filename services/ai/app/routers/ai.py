"""AI router for RAG Q&A endpoints."""
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.rag_service import get_rag_service
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])


class AskRequest(BaseModel):
    """Request model for /ai/ask endpoint."""
    course_id: UUID = Field(..., description="Course UUID to search within")
    question: str = Field(..., min_length=1, description="User's question")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")


class SourceInfo(BaseModel):
    """Source chunk information."""
    chunk_id: str
    asset_id: str
    score: float


class AskResponse(BaseModel):
    """Response model for /ai/ask endpoint."""
    answer: str
    sources: list[SourceInfo]


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    db: Session = Depends(get_db)
) -> AskResponse:
    """
    Ask a question about course content using RAG.
    
    Steps:
    1. Retrieve semantically similar chunks from course
    2. Generate answer using LLM with retrieved context
    3. Return answer with source citations
    
    Example:
        POST /ai/ask
        {
            "course_id": "123e4567-e89b-12d3-a456-426614174000",
            "question": "What is dependency injection?",
            "top_k": 5
        }
    """
    try:
        logger.info(
            f"Received RAG query for course {request.course_id}: "
            f"'{request.question[:50]}...'"
        )
        
        rag_service = get_rag_service(db)
        result = rag_service.ask(
            course_id=request.course_id,
            question=request.question,
            top_k=request.top_k
        )
        
        return AskResponse(
            answer=result["answer"],
            sources=[SourceInfo(**src) for src in result["sources"]]
        )
        
    except Exception as e:
        logger.exception(f"Error processing RAG query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "ai-service"}
