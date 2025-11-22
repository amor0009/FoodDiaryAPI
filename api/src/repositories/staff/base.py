from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models.staff import Staff


class BaseStaffRepository(ABC):
    @abstractmethod
    async def find_by_login(self, session: AsyncSession, login: str) -> Staff | None: ...
