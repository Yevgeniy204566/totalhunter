import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# blacksea.py валидирует эти переменные на импорте (см. спеку) — без них
# упадёт весь набор тестов, а не только тесты BlackSea.
os.environ.setdefault("BLACKSEA_CLIENT_ID",     "test-blacksea-client-id")
os.environ.setdefault("BLACKSEA_CLIENT_SECRET", "test-blacksea-client-secret")
os.environ.setdefault("BLACKSEA_PRODUCT_ID",    "test-blacksea-product-id")

from database import get_db
from models import Base
from main import app

# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_db():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncTestSession = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with AsyncTestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_test_db):
    """Direct DB session for manipulating test state (e.g., banning a user)."""
    async for session in app.dependency_overrides[get_db]():
        yield session
