from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


@sa_event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, _connection_record):
    """Apply performance and safety pragmas on every new SQLite connection."""
    cursor = dbapi_connection.cursor()
    # WAL allows concurrent readers + one writer without blocking
    cursor.execute("PRAGMA journal_mode=WAL")
    # NORMAL is safe with WAL and much faster than FULL
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Enforce referential integrity
    cursor.execute("PRAGMA foreign_keys=ON")
    # 8 MB page cache (negative = kibibytes)
    cursor.execute("PRAGMA cache_size=-8000")
    # Store temp tables in memory
    cursor.execute("PRAGMA temp_store=MEMORY")
    # Busy-wait up to 10 s before raising OperationalError
    cursor.execute("PRAGMA busy_timeout=10000")
    cursor.close()
    logger.debug("SQLite pragmas applied (WAL, NORMAL sync, FK on, 8 MB cache)")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
