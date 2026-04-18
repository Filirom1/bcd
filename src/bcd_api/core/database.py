"""Database connection and session management."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

from .config import settings

# SQLite-specific settings for better concurrency and foreign key support
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False,  # Allow SQLite usage across threads
    }
    # Use QueuePool with single connection for SQLite
    # This serializes database access while allowing concurrent HTTP requests
    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        poolclass=QueuePool,
        pool_size=1,           # Only 1 connection in the pool
        max_overflow=0,        # No additional connections allowed
        pool_pre_ping=True,    # Verify connections before using
        echo=settings.log_level == "DEBUG",
    )

    # Enable foreign key support and performance optimizations for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()

        # Foreign key enforcement
        cursor.execute("PRAGMA foreign_keys=ON")

        # Performance optimizations (2-3x faster writes, better for legacy hardware)
        cursor.execute("PRAGMA journal_mode=WAL")       # Write-Ahead Logging for concurrent reads
        cursor.execute("PRAGMA synchronous=NORMAL")     # Safe with WAL, much faster than FULL
        cursor.execute("PRAGMA cache_size=-64000")      # 64MB cache (negative = KB)
        cursor.execute("PRAGMA temp_store=MEMORY")      # Store temp tables in memory

        cursor.close()
else:
    # PostgreSQL or other database
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        echo=settings.log_level == "DEBUG",
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.

    Yields:
        Session: SQLAlchemy database session.

    Example:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
