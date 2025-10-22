"""add_attempts_column_to_listening_sessions

Revision ID: f0277ea1dc25
Revises: 20251023_update_sentences
Create Date: 2025-10-22 21:06:50.969104

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0277ea1dc25'
down_revision: Union[str, Sequence[str], None] = '20251023_update_sentences'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add attempts column to listening_sessions table
    op.add_column('listening_sessions', sa.Column('attempts', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove attempts column from listening_sessions table
    op.drop_column('listening_sessions', 'attempts')
