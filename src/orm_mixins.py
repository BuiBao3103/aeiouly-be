from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func


class SoftDeleteMixin:
    """Mixin to add soft-delete support via `deleted_at` timestamp.

    Rows are considered active when deleted_at IS NULL.
    """
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps."""
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)


