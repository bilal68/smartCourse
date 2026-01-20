"""Enable pgvector extension

Revision ID: enable_pgvector
Revises: c9a0e336d1ea
Create Date: 2026-01-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'enable_pgvector'
down_revision = 'c9a0e336d1ea'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector extension must be installed separately on the PostgreSQL server
    # using: CREATE EXTENSION vector;
    pass


def downgrade() -> None:
    pass

