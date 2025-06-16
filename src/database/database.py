from typing import AsyncGenerator
from sqlalchemy import NullPool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from src.core.config import config
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from src.logging_config import logger


engine = create_async_engine(config.database_url, echo=True, poolclass=NullPool)
async_session_maker = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        logger.info(f"Connected to database: {config.database_url}")
        yield session
