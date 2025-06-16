from src.daos.base_dao import BaseDAO
from src.models.staff import Staff
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class StaffDAO(BaseDAO):
    model = Staff

    @classmethod
    # Поиск сотрудника по логину
    async def find_by_login(
            cls,
            session: AsyncSession,
            login: str,
    ) -> Staff | None:
        query = select(cls.model).where(
            cls.model.login == login
        )

        result = await session.execute(query)
        return result.scalar_one_or_none()
