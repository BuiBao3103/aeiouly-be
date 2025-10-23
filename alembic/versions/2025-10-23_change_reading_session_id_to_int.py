"""change_reading_session_id_to_int

Revision ID: bb2a77b15d12
Revises: f0277ea1dc25
Create Date: 2025-10-23 07:12:28.041403

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb2a77b15d12'
down_revision: Union[str, Sequence[str], None] = 'f0277ea1dc25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the existing table and recreate with integer ID
    op.drop_table('reading_sessions')
    
    # Create new table with integer ID
    op.create_table('reading_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('level', sa.String(length=2), nullable=False),
        sa.Column('genre', sa.String(length=50), nullable=False),
        sa.Column('topic', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('is_custom', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_reading_sessions_id'), 'reading_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_reading_sessions_user_id'), 'reading_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_reading_sessions_level'), 'reading_sessions', ['level'], unique=False)
    op.create_index(op.f('ix_reading_sessions_genre'), 'reading_sessions', ['genre'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the table
    op.drop_table('reading_sessions')
    
    # Recreate with UUID ID (original structure)
    op.create_table('reading_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('level', sa.String(length=2), nullable=False),
        sa.Column('genre', sa.String(length=50), nullable=False),
        sa.Column('topic', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('is_custom', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_reading_sessions_id'), 'reading_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_reading_sessions_user_id'), 'reading_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_reading_sessions_level'), 'reading_sessions', ['level'], unique=False)
    op.create_index(op.f('ix_reading_sessions_genre'), 'reading_sessions', ['genre'], unique=False)
