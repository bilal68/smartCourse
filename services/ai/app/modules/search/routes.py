"""Search routes."""

from fastapi import APIRouter, Depends
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