from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import config
from src.database.database import get_async_session
from src.database.fill_database import fill_database
from src.logging_config import logger


database_router = APIRouter(tags=["Database"])


# Эндпоинт для заполнения базы данных из файла
@database_router.post('/fill')
async def fill_db(db: AsyncSession = Depends(get_async_session)):
    await db.execute(text("TRUNCATE TABLE product RESTART IDENTITY CASCADE"))
    await db.commit()
    logger.info("Product table truncated successfully")
    await fill_database(db, config.FILE_PATH)
    logger.info(f"Database successfully filled from {config.FILE_PATH}")
    return HTTPException(
        status_code=status.HTTP_200_OK,
        detail='Database filled successfully'
    )
