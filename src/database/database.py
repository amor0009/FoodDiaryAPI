from typing import AsyncGenerator
from sqlalchemy import NullPool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from src.core.config import DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME, DB_PORT_DOCKER
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT_DOCKER}/{DB_NAME}"

engine = create_async_engine(DATABASE_URL, echo=True, poolclass=NullPool)
async_session_maker = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        print(f"Connected to database:{DATABASE_URL}")
        yield session
