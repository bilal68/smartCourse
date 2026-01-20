"""Add article content upload fields to learning_assets

Revision ID: add_content_upload_fields
Revises: 9a3c0b36d3ff
Create Date: 2026-01-20 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_content_upload_fields'
down_revision = '9a3c0b36d3ff'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create AssetStatus enum type
    asset_status = postgresql.ENUM(
        'draft',
        'upload_pending',
        'uploaded',
        'ready',
        'rejected',
        'archived',
        name='asset_status'
    )
    asset_status.create(op.get_bind(), checkfirst=True)

    # Add new columns to learning_assets
    op.add_column('learning_assets', sa.Column('status', asset_status, server_default='draft', nullable=False))
    op.add_column('learning_assets', sa.Column('content_format', sa.String(50), server_default='EDITOR_JSON', nullable=False))
    op.add_column('learning_assets', sa.Column('storage_provider', sa.String(50), server_default='S3', nullable=False))
    op.add_column('learning_assets', sa.Column('bucket', sa.String(255), nullable=True))
    op.add_column('learning_assets', sa.Column('key', sa.String(1024), nullable=True))
    op.add_column('learning_assets', sa.Column('expected_content_type', sa.String(100), nullable=True))
    op.add_column('learning_assets', sa.Column('size_bytes', sa.BigInteger(), nullable=True))
    op.add_column('learning_assets', sa.Column('content_hash', sa.String(64), nullable=True))
    op.add_column('learning_assets', sa.Column('version', sa.Integer(), server_default='1', nullable=False))
    op.add_column('learning_assets', sa.Column('validation_error', sa.Text(), nullable=True))

    # Create indexes
    op.create_index(op.f('ix_learning_assets_status'), 'learning_assets', ['status'])
    op.create_index(op.f('ix_learning_assets_bucket'), 'learning_assets', ['bucket'])
    op.create_index(op.f('ix_learning_assets_key'), 'learning_assets', ['key'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_learning_assets_key'), table_name='learning_assets')
    op.drop_index(op.f('ix_learning_assets_bucket'), table_name='learning_assets')
    op.drop_index(op.f('ix_learning_assets_status'), table_name='learning_assets')

    # Drop columns
    op.drop_column('learning_assets', 'validation_error')
    op.drop_column('learning_assets', 'version')
    op.drop_column('learning_assets', 'content_hash')
    op.drop_column('learning_assets', 'size_bytes')
    op.drop_column('learning_assets', 'expected_content_type')
    op.drop_column('learning_assets', 'key')
    op.drop_column('learning_assets', 'bucket')
    op.drop_column('learning_assets', 'storage_provider')
    op.drop_column('learning_assets', 'content_format')
    op.drop_column('learning_assets', 'status')

    # Drop enum type
    asset_status = postgresql.ENUM(
        'draft',
        'upload_pending',
        'uploaded',
        'ready',
        'rejected',
        'archived',
        name='asset_status'
    )
    asset_status.drop(op.get_bind(), checkfirst=True)
