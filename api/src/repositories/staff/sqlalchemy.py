from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models.staff import Staff
from api.src.repositories.staff.base import BaseStaffRepository
from api.src.repositories.crud import CrudOperations


@dataclass(slots=True)
class SqlAlchemyStaffRepository(BaseStaffRepository):
    def __init__(self) -> None:
        self._crud = CrudOperations(Staff)

    async def find_by_login(self, session: AsyncSession, login: str) -> Staff | None:
        query = select(Staff).where(Staff.login == login)
        result = await session.execute(query)
        return result.scalar_one_or_none()
    