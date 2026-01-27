"""Create chunk_embeddings table

Revision ID: create_chunk_embeddings
Revises: 7f086b141cdc
Create Date: 2026-01-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'create_chunk_embeddings'
down_revision = '7f086b141cdc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'chunk_embeddings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('chunk_id', UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column('course_id', UUID(as_uuid=True), nullable=False),
        # Store embeddings as TEXT (JSON array format) until pgvector extension is installed
        # Can be converted to Vector(1536) after: CREATE EXTENSION vector;
        sa.Column('embedding', sa.Text(), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        # ForeignKey to content_chunks removed - table may not exist yet
    )
    
    # Index on course_id for filtering
    op.create_index(op.f('ix_chunk_embeddings_course_id'), 'chunk_embeddings', ['course_id'])
    
    # Note: pgvector index will be added after extension is installed


def downgrade() -> None:
    op.drop_index(op.f('ix_chunk_embeddings_course_id'), table_name='chunk_embeddings')
    op.drop_table('chunk_embeddings')

