"""create_reading_sessions_table_manual

Revision ID: cabf1fb4f305
Revises: 7d49a4efd904
Create Date: 2025-10-23 06:02:48.976776

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'cabf1fb4f305'
down_revision: Union[str, Sequence[str], None] = '20251023_update_sentences'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create reading_sessions table
    op.create_table('reading_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('level', sa.String(2), nullable=False),
        sa.Column('genre', sa.String(50), nullable=False),
        sa.Column('topic', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('is_custom', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('deleted_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='reading_sessions_user_id_fkey'),
    )
    
    # Create indexes
    op.create_index('ix_reading_sessions_id', 'reading_sessions', ['id'])
    op.create_index('ix_reading_sessions_user_id', 'reading_sessions', ['user_id'])
    op.create_index('ix_reading_sessions_level', 'reading_sessions', ['level'])
    op.create_index('ix_reading_sessions_genre', 'reading_sessions', ['genre'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_reading_sessions_genre', table_name='reading_sessions')
    op.drop_index('ix_reading_sessions_level', table_name='reading_sessions')
    op.drop_index('ix_reading_sessions_user_id', table_name='reading_sessions')
    op.drop_index('ix_reading_sessions_id', table_name='reading_sessions')
    
    # Drop table
    op.drop_table('reading_sessions')
