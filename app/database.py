from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings
from app.core.sqlite_config import configure_sqlite, run_optimize

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)


# Configure SQLite optimizations on new connections
@event.listens_for(engine.sync_engine, "connect")
def on_connect(dbapi_conn, connection_record):
    """Apply SQLite configuration pragmas on new connections."""
    # Create a minimal connection wrapper for the configure function
    class _SimpleConnection:
        def __init__(self, dialect, connection):
            self.dialect = dialect
            self.connection = connection

    wrapper = _SimpleConnection(engine.dialect, dbapi_conn)
    configure_sqlite(wrapper)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.

    Yields:
        AsyncSession: Database session for use in endpoints.

    Example:
        ```python
        @app.get("/users/")
        async def get_users(session: AsyncSession = Depends(get_session)):
            result = await session.execute(select(User))
            return result.scalars().all()
        ```
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.

    This function creates all tables defined in the ORM models.
    Use this for development only. For production, use Alembic migrations.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connection and run optimization."""
    # Run PRAGMA optimize before closing to update query planner stats
    async with engine.connect() as conn:
        await conn.run_sync(run_optimize)
    await engine.dispose()
