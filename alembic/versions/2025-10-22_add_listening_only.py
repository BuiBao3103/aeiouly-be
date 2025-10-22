"""Add listening module tables only

Revision ID: listening_only_001
Revises: 79b0d600f4b4
Create Date: 2025-10-22 04:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'listening_only_001'
down_revision: Union[str, Sequence[str], None] = '79b0d600f4b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create listen_lessons table
    op.create_table('listen_lessons',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('youtube_url', sa.String(length=500), nullable=False),
    sa.Column('level', sa.String(length=10), nullable=False),
    sa.Column('tags', sa.JSON(), nullable=True),
    sa.Column('total_sentences', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_listen_lessons_id'), 'listen_lessons', ['id'], unique=False)
    
    # Create sentences table
    op.create_table('sentences',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('lesson_id', sa.Integer(), nullable=False),
    sa.Column('index', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('translation', sa.Text(), nullable=True),
    sa.Column('start_time', sa.Float(), nullable=False),
    sa.Column('end_time', sa.Float(), nullable=False),
    sa.Column('normalized_text', sa.Text(), nullable=True),
    sa.Column('alternatives', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['lesson_id'], ['listen_lessons.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sentences_id'), 'sentences', ['id'], unique=False)
    op.create_index(op.f('ix_sentences_lesson_id'), 'sentences', ['lesson_id'], unique=False)
    
    # Create listening_sessions table
    op.create_table('listening_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('lesson_id', sa.Integer(), nullable=False),
    sa.Column('current_sentence_index', sa.Integer(), nullable=True),
    sa.Column('last_studied', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['lesson_id'], ['listen_lessons.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_listening_sessions_id'), 'listening_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_listening_sessions_lesson_id'), 'listening_sessions', ['lesson_id'], unique=False)
    op.create_index(op.f('ix_listening_sessions_user_id'), 'listening_sessions', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_listening_sessions_user_id'), table_name='listening_sessions')
    op.drop_index(op.f('ix_listening_sessions_lesson_id'), table_name='listening_sessions')
    op.drop_index(op.f('ix_listening_sessions_id'), table_name='listening_sessions')
    op.drop_table('listening_sessions')
    op.drop_index(op.f('ix_sentences_lesson_id'), table_name='sentences')
    op.drop_index(op.f('ix_sentences_id'), table_name='sentences')
    op.drop_table('sentences')
    op.drop_index(op.f('ix_listen_lessons_id'), table_name='listen_lessons')
    op.drop_table('listen_lessons')

