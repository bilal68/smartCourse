"""make_embedding_dimension_flexible

Revision ID: make_embeddings_flexible
Revises: create_chunk_embeddings
Create Date: 2026-01-22 14:38:00.000000

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = 'make_embeddings_flexible'
down_revision = 'create_chunk_embeddings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, ensure pgvector extension is installed
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Drop the existing table with fixed dimensions
    op.drop_table('chunk_embeddings')
    
    # Recreate table with flexible vector dimensions
    from sqlalchemy import String, DateTime, ForeignKey, Index
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    from pgvector.sqlalchemy import Vector
    from datetime import datetime
    
    op.create_table(
        'chunk_embeddings',
        sa.Column('id', PG_UUID(as_uuid=True), primary_key=True),
        sa.Column('chunk_id', PG_UUID(as_uuid=True), ForeignKey("content_chunks.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column('course_id', PG_UUID(as_uuid=True), nullable=False),
        sa.Column('embedding', Vector(), nullable=False),  # No fixed dimension!
        sa.Column('model_name', String(100), nullable=False),
        sa.Column('created_at', DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', DateTime(timezone=True), nullable=False),
    )
    
    # Add indexes
    op.create_index('ix_chunk_embeddings_chunk_id', 'chunk_embeddings', ['chunk_id'])
    op.create_index('ix_chunk_embeddings_course_id', 'chunk_embeddings', ['course_id'])


def downgrade() -> None:
    # Drop the flexible table and recreate with fixed dimensions
    op.drop_table('chunk_embeddings')
    
    # Recreate with the old fixed dimensions
    from sqlalchemy import String, DateTime, ForeignKey
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    from pgvector.sqlalchemy import Vector
    
    op.create_table(
        'chunk_embeddings',
        sa.Column('id', PG_UUID(as_uuid=True), primary_key=True),
        sa.Column('chunk_id', PG_UUID(as_uuid=True), ForeignKey("content_chunks.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column('course_id', PG_UUID(as_uuid=True), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),  # Fixed 1536 dimensions
        sa.Column('model_name', String(100), nullable=False),
        sa.Column('created_at', DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', DateTime(timezone=True), nullable=False),
    )