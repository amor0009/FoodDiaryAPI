from dataclasses import dataclass
from datetime import date, timedelta, datetime
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models.user_weight import UserWeight
from api.src.repositories.user_weight.base import BaseUserWeightRepository
from api.src.repositories.crud import CrudOperations


@dataclass(slots=True)
class SqlAlchemyUserWeightRepository(BaseUserWeightRepository):
    def __init__(self) -> None:
        self._crud = CrudOperations(UserWeight)

    async def get_by_date(self, session: AsyncSession, user_id: UUID, target_date: date) -> UserWeight | None:
        target_datetime = datetime.combine(target_date, datetime.min.time())
        next_day = target_datetime + timedelta(days=1)

        query = select(UserWeight).where(
            and_(
                UserWeight.user_id == user_id,
                UserWeight.created_at >= target_datetime,
                UserWeight.created_at < next_day
            )
        ).order_by(UserWeight.created_at.desc()).limit(1)

        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def create_or_update(
            self,
            session: AsyncSession,
            user_id: UUID,
            weight: float,
    ) -> UserWeight:

        user_weight = UserWeight(
            user_id=user_id,
            weight=weight,
            created_at=datetime.now()
        )
        session.add(user_weight)
        await session.commit()
        await session.refresh(user_weight)
        return user_weight

    async def get_last_30_days(self, session: AsyncSession, user_id: UUID) -> list[UserWeight] | None:
        thirty_days_ago = datetime.now() - timedelta(days=30)
        query = select(UserWeight).where(
            and_(
                UserWeight.user_id == user_id,
                UserWeight.created_at >= thirty_days_ago
            )
        ).order_by(UserWeight.created_at)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def delete(self, session: AsyncSession, user_weight_id: UUID) -> None:
        await self._crud.delete(session, user_weight_id)
