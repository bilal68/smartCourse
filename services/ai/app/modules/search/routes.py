"""Search routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.search.service import SearchService
from app.api.schemas import SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def semantic_search(
    search_request: SearchRequest,
    db: Session = Depends(get_db),
):
    """Perform semantic search across content chunks using pgvector cosine distance."""
    search_service = SearchService(db)
    return search_service.semantic_search(search_request)


@router.post("/chat")
async def contextual_chat(
    request: dict,  # {"question": "...", "course_ids": [...], "mode": "student" or "instructor"}
    db: Session = Depends(get_db)
):
    """
    Intelligent Learning Assistant - Full RAG with streaming responses.
    
    Supports:
    A. Contextual Q&A for Students
    B. Content Enhancement for Instructors (summaries, objectives, quiz questions)
    """
    question = request.get("question", "")
    course_ids = request.get("course_ids", [])
    mode = request.get("mode", "student")  # "student" or "instructor"
    
    if not question:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Question is required")
    
    search_service = SearchService(db)
    response_generator = search_service.contextual_chat(
        question=question,
        course_ids=course_ids,
        mode=mode
    )
    
    return StreamingResponse(response_generator, media_type="text/plain")