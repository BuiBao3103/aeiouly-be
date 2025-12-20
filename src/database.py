from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import MetaData, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import with_loader_criteria
from src.config import get_database_url

# PostgreSQL naming conventions
POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

metadata = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)

# Create async database engine
database_url = get_database_url()
# Replace postgresql+asyncpg:// with postgresql+asyncpg:// for async
if database_url.startswith("postgresql+psycopg2://"):
    database_url = database_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
elif not database_url.startswith("postgresql+asyncpg://"):
    # If it's already asyncpg or needs conversion
    if "postgresql://" in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    database_url,
    echo=False,
    future=True,
    connect_args={
        "server_settings": {
            "timezone": "UTC"
        }
    } if "postgresql" in database_url else {}
)

# Note: For asyncpg, timezone is set via connect_args above
# This is more reliable than using event listeners for async connections

# Create AsyncSessionLocal class
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create Base class with naming conventions
Base = declarative_base(metadata=metadata)

# Apply a global filter to exclude soft-deleted rows on all ORM SELECTs
# Note: For async, the event listener works similarly but with AsyncSession
try:
    from src.orm_mixins import SoftDeleteMixin

    @event.listens_for(AsyncSession, "do_orm_execute")
    def _add_soft_delete_filter(execute_state):
        # Only apply to ORM SELECT statements
        if not execute_state.is_select:
            return

        # Allow bypass via execution options:
        # - include_deleted=True: do not apply the global filter
        # - only_deleted=True: filter to only deleted rows
        opts = getattr(execute_state, "local_execution_options", {}) or {}
        if opts.get("include_deleted"):
            return

        only_deleted = bool(opts.get("only_deleted"))
        predicate_factory = (lambda cls: cls.deleted_at.isnot(None)) if only_deleted else (lambda cls: cls.deleted_at.is_(None))

        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                SoftDeleteMixin,
                predicate_factory,
                include_aliases=True,
            )
        )
except Exception:
    # If anything goes wrong, skip the global filter to avoid breaking the app
    pass

# Dependency to get async database session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()