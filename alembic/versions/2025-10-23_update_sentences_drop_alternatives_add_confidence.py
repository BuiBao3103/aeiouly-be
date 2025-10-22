"""
Update sentences table: drop alternatives, add confidence

Revision ID: 20251023_update_sentences
Revises: 2025-10-22_add_listening_only
Create Date: 2025-10-23
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251023_update_sentences'
down_revision = 'remove_last_studied_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add confidence column
    op.add_column('sentences', sa.Column('confidence', sa.Float(), nullable=True))
    # Drop alternatives column if exists
    with op.batch_alter_table('sentences') as batch_op:
        try:
            batch_op.drop_column('alternatives')
        except Exception:
            # Column might already be removed in some environments
            pass
    # Drop tags from listen_lessons if exists
    with op.batch_alter_table('listen_lessons') as batch_op:
        try:
            batch_op.drop_column('tags')
        except Exception:
            pass


def downgrade() -> None:
    # Recreate alternatives column as JSON/null
    with op.batch_alter_table('sentences') as batch_op:
        batch_op.add_column(sa.Column('alternatives', sa.JSON(), nullable=True))
    # Drop confidence column
    with op.batch_alter_table('sentences') as batch_op:
        batch_op.drop_column('confidence')
    # Recreate tags column
    with op.batch_alter_table('listen_lessons') as batch_op:
        batch_op.add_column(sa.Column('tags', sa.JSON(), nullable=True))


