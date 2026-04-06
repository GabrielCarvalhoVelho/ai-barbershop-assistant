from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.core.config import settings


def _create_engine():
    if settings.database_url.startswith("sqlite"):
        # SQLite não suporta pool configurável — usa StaticPool (in-memory e dev)
        return create_async_engine(
            settings.database_url,
            echo=settings.debug,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    # PostgreSQL (dev local e Supabase)
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_size=5,
        max_overflow=10,
        pool_recycle=300,  # descarta conexões após 5 min — evita "idle connection" no Supabase
        pool_pre_ping=True,  # valida conexão antes de usar — detecta drops silenciosos
    )


engine = _create_engine()

async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_session():
    """Uma transação por request: commit no sucesso, rollback em qualquer erro."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine():
    await engine.dispose()
