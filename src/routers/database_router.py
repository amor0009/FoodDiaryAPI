from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import FILE_PATH
from src.database.database import get_async_session
from src.database.fill_database import fill_database


database_router = APIRouter()


@database_router.post('/fill')
async def fill_db(db: AsyncSession = Depends(get_async_session)):
    await fill_database(db, FILE_PATH)
    return HTTPException(
        status_code=status.HTTP_200_OK,
        detail='Database filled successfully'
    )
