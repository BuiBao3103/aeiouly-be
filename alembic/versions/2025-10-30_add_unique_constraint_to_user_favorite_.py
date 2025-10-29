"""add unique constraint to user_favorite_videos

Revision ID: e0285054b23e
Revises: 1ff29afae098
Create Date: 2025-10-30 02:48:20.413845

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0285054b23e'
down_revision: Union[str, Sequence[str], None] = '1ff29afae098'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add unique constraint on user_id and youtube_url combination
    op.create_unique_constraint(
        'uq_user_favorite_videos_user_youtube',
        'user_favorite_videos',
        ['user_id', 'youtube_url']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove unique constraint
    op.drop_constraint(
        'uq_user_favorite_videos_user_youtube',
        'user_favorite_videos',
        type_='unique'
    )
