"""Content management routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.content.service import ContentService

router = APIRouter(prefix="/content", tags=["content"])


@router.post("/generate-embeddings")
async def generate_embeddings(
    course_id: Optional[UUID] = None,
    force_regenerate: bool = Query(default=True, description="Regenerate embeddings even if they exist"),
    db: Session = Depends(get_db)
):
    """Generate embeddings for content chunks using the configured provider."""
    content_service = ContentService(db)
    return content_service.generate_embeddings(course_id, force_regenerate)