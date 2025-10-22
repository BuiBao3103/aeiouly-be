"""Remove last_studied from listening_sessions

Revision ID: remove_last_studied_001
Revises: listening_only_001
Create Date: 2025-10-22 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'remove_last_studied_001'
down_revision: Union[str, Sequence[str], None] = 'listening_only_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove last_studied column from listening_sessions table
    op.drop_column('listening_sessions', 'last_studied')


def downgrade() -> None:
    """Downgrade schema."""
    # Add last_studied column back to listening_sessions table
    op.add_column('listening_sessions', 
                  sa.Column('last_studied', sa.DateTime(timezone=True), nullable=True))
