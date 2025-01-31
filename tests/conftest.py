import asyncio
from typing import AsyncGenerator
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from src.core.config import (DB_HOST_TEST, DB_NAME_TEST, DB_PASS_TEST, DB_PORT_TEST, DB_USER_TEST)
from src.database.database import get_async_session, Base
from src.main import app

# DATABASE
DATABASE_URL_TEST = f"postgresql+asyncpg://{DB_USER_TEST}:{DB_PASS_TEST}@{DB_HOST_TEST}:{DB_PORT_TEST}/{DB_NAME_TEST}"
engine_test = create_async_engine(DATABASE_URL_TEST, poolclass=NullPool)
async_session_maker = sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)


async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


app.dependency_overrides[get_async_session] = override_get_async_session


@pytest.fixture(autouse=True, scope='session')
async def prepare_database():
    print("\nSetting up the database...")
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Пропускаем выполнение тестов
    yield
    print("\nTearing down the database...")
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


client = TestClient(app)


@pytest.fixture(scope="session")
async def ac() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
