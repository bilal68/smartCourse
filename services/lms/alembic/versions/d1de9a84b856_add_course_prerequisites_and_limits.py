"""add_course_prerequisites_and_limits

Revision ID: d1de9a84b856
Revises: 29d2e3c647d0
Create Date: 2026-01-10 22:43:24.094233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1de9a84b856'
down_revision: Union[str, Sequence[str], None] = '29d2e3c647d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add max_students column to courses table
    op.add_column('courses', sa.Column('max_students', sa.Integer(), nullable=True))
    
    # Create course_prerequisites association table
    op.create_table(
        'course_prerequisites',
        sa.Column('course_id', sa.UUID(), nullable=False),
        sa.Column('prerequisite_course_id', sa.UUID(), nullable=False),
        sa.Column('is_mandatory', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['prerequisite_course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('course_id', 'prerequisite_course_id'),
        sa.CheckConstraint('course_id != prerequisite_course_id', name='ck_no_self_prerequisite')
    )
    
    # Create index for faster prerequisite lookups
    op.create_index('ix_course_prerequisites_course_id', 'course_prerequisites', ['course_id'])
    op.create_index('ix_course_prerequisites_prerequisite_id', 'course_prerequisites', ['prerequisite_course_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_course_prerequisites_prerequisite_id', table_name='course_prerequisites')
    op.drop_index('ix_course_prerequisites_course_id', table_name='course_prerequisites')
    
    # Drop course_prerequisites table
    op.drop_table('course_prerequisites')
    
    # Drop max_students column from courses
    op.drop_column('courses', 'max_students')
