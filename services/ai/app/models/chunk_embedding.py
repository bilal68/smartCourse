"""ChunkEmbedding model for storing vector embeddings."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from pgvector.sqlalchemy import Vector

from app.db.base import Base


class ChunkEmbedding(Base):
    """
    Stores vector embeddings for content chunks.
    One embedding per chunk for semantic search/RAG.
    """
    __tablename__ = "chunk_embeddings"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    chunk_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        ForeignKey("content_chunks.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    course_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    
    # Vector embedding - flexible dimension based on model
    # 384 for sentence-transformers (multi-qa-MiniLM-L6-cos-v1)
    # 1536 for OpenAI (text-embedding-3-small)
    embedding: Mapped[Vector] = mapped_column(Vector(None), nullable=False)
    
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )

    # Relationship to ContentChunk
    chunk: Mapped["ContentChunk"] = relationship("ContentChunk", back_populates="embedding")

    # Vector similarity index created via Alembic migration
    __table_args__ = (
        Index('ix_chunk_embeddings_course_id', 'course_id'),
    )

    def __repr__(self) -> str:
        return f"<ChunkEmbedding(id={self.id}, chunk_id={self.chunk_id}, model={self.model_name})>"
