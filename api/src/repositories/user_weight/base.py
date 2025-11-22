from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models.user_weight import UserWeight


class BaseUserWeightRepository(ABC):
    @abstractmethod
    async def get_by_date(self, session: AsyncSession, user_id: UUID, target_date: date) -> UserWeight | None: ...

    @abstractmethod
    async def create_or_update(
        self,
        session: AsyncSession,
        user_id: UUID,
        weight: float,
    ) -> UserWeight: ...

    @abstractmethod
    async def get_last_30_days(self, session: AsyncSession, user_id: UUID) -> list[UserWeight] | None: ...

    @abstractmethod
    async def delete(self, session: AsyncSession, user_weight_id: UUID) -> None: ...
