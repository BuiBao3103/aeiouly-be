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

# Dependency to get database session
def get_db():
    db: Session = SessionLocal()
    try:
        # Apply global soft-delete filters: only load rows where deleted_at is NULL
        from src.orm_mixins import SoftDeleteMixin
        yield db.execution_options(
            loader_criteria=[
                with_loader_criteria(SoftDeleteMixin, lambda cls: cls.deleted_at.is_(None), include_aliases=True)
            ]
        )
    finally:
        db.close()