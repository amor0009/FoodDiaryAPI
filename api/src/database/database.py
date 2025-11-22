from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aioboto3 as aioboto3
from sqlalchemy import NullPool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from api.src.core.config import config
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from api.logging_config import logger


engine = create_async_engine(config.database_url, echo=True, poolclass=NullPool)
async_session_maker = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


s3_session = aioboto3.Session()


@asynccontextmanager
async def s3_client():
    async with s3_session.client(
        service_name="s3",
        region_name=config.S3_REGION,
        endpoint_url=config.S3_ENDPOINT,
        aws_access_key_id=config.S3_KEY_ID,
        aws_secret_access_key=config.S3_SECRET_ACCESS_KEY,
    ) as s3_client:
        yield s3_client


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        logger.info(f"Connected to database: {config.database_url}")
        yield session
