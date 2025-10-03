from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, with_loader_criteria
from sqlalchemy import event
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

# Create database engine
database_url = get_database_url()
engine = create_engine(database_url)

# Ensure database sessions use UTC timezone (PostgreSQL)
def _set_timezone_utc(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("SET TIME ZONE 'UTC'")
        cursor.close()
    except Exception:
        # Ignore if DB does not support this (e.g., SQLite)
        pass

event.listen(engine, "connect", _set_timezone_utc)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class with naming conventions
Base = declarative_base(metadata=metadata)

# Apply a global filter to exclude soft-deleted rows on all ORM SELECTs
try:
    from src.orm_mixins import SoftDeleteMixin

    @event.listens_for(Session, "do_orm_execute")
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

# Dependency to get database session
def get_db():
    db: Session = SessionLocal()
    try:
        # Keep dependency simple and robust to avoid contextmanager errors
        yield db
    finally:
        db.close()