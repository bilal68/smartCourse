"""create_content_chunks_table

Revision ID: 7f086b141cdc
Revises: enable_pgvector
Create Date: 2026-01-20 11:44:08.303104

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '7f086b141cdc'
down_revision = 'enable_pgvector'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing content_chunks table created by initial migration
    op.drop_index(op.f('ix_content_chunks_course_id'), table_name='content_chunks')
    op.drop_index(op.f('ix_content_chunks_asset_id'), table_name='content_chunks')
    op.drop_table('content_chunks')
    
    # Recreate with new schema
    op.create_table(
        'content_chunks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('course_id', UUID(as_uuid=True), nullable=False),
        sa.Column('asset_id', UUID(as_uuid=True), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('start_char', sa.Integer(), nullable=True),
        sa.Column('end_char', sa.Integer(), nullable=True),
        sa.Column('char_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    op.create_index(op.f('ix_content_chunks_course_id'), 'content_chunks', ['course_id'])
    op.create_index(op.f('ix_content_chunks_asset_id'), 'content_chunks', ['asset_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_content_chunks_asset_id'), table_name='content_chunks')
    op.drop_index(op.f('ix_content_chunks_course_id'), table_name='content_chunks')
    op.drop_table('content_chunks')