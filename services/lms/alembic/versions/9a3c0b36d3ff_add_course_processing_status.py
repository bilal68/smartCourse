"""add_course_processing_status

Revision ID: 9a3c0b36d3ff
Revises: d1de9a84b856
Create Date: 2026-01-13 12:40:50.488899

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a3c0b36d3ff'
down_revision: Union[str, Sequence[str], None] = 'd1de9a84b856'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add processing status tracking to courses table."""
    # Create the new enum type
    processing_status_enum = sa.Enum(
        'not_started', 'processing', 'ready', 'failed',
        name='course_processing_status',
        create_type=True
    )
    processing_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Add processing_status column with default value
    op.add_column(
        'courses',
        sa.Column(
            'processing_status',
            sa.Enum('not_started', 'processing', 'ready', 'failed', name='course_processing_status'),
            server_default='not_started',
            nullable=False
        )
    )
    
    # Add processing_error column (nullable, for error messages)
    op.add_column(
        'courses',
        sa.Column('processing_error', sa.Text(), nullable=True)
    )
    
    # Add processed_at column (nullable, timestamp when processing completed)
    op.add_column(
        'courses',
        sa.Column('processed_at', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    """Remove processing status tracking from courses table."""
    # Drop the columns
    op.drop_column('courses', 'processed_at')
    op.drop_column('courses', 'processing_error')
    op.drop_column('courses', 'processing_status')
    
    # Drop the enum type
    sa.Enum(name='course_processing_status').drop(op.get_bind(), checkfirst=True)
