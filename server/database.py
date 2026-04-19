"""
database.py — Async PostgreSQL connection for Total Hunter SaaS.

Драйвер: asyncpg (postgresql+asyncpg://)
Движок:  create_async_engine — FastAPI использует его полную мощь.

DATABASE_URL из переменной окружения:
  Локально:  postgresql+asyncpg://hunter:hunter@localhost:5432/totalhunter
  GCP VM:    postgresql+asyncpg://hunter:PASS@/totalhunter?host=/cloudsql/PROJECT:REGION:INSTANCE
  (Cloud SQL через сокет — если перейдём на Cloud SQL в будущем)
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://hunter:hunter@localhost:5432/totalhunter",
)

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # отсекает мёртвые соединения из пула
    pool_size=10,
    max_overflow=20,
    echo=False,           # True для отладки SQL-запросов
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,  # объекты не протухают после commit — удобно в async
)


async def get_db() -> AsyncSession:
    """
    FastAPI dependency — открывает async-сессию и закрывает после запроса.

    Использование в роуте:
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        yield session
