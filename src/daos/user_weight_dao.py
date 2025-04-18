from datetime import date, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from src.daos.base_dao import BaseDAO
from src.models.user_weight import UserWeight


class UserWeightDAO(BaseDAO):
    model = UserWeight

    @classmethod
    async def get_by_date(cls, session: AsyncSession, user_id: int, target_date: date):
        query = select(cls.model).where(
            and_(
                cls.model.user_id == user_id,
                cls.model.recorded_at == target_date
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def create_or_update(
            cls,
            session: AsyncSession,
            user_id: int,
            weight: float,
            target_date: date
    ):
        # Проверяем существующую запись
        existing = await cls.get_by_date(session, user_id, target_date)

        if existing:
            existing.weight = weight
        else:
            existing = cls.model(
                user_id=user_id,
                weight=weight,
                recorded_at=target_date
            )
            session.add(existing)

        await session.commit()
        await session.refresh(existing)
        return existing

    @classmethod
    async def get_last_30_days(cls, session: AsyncSession, user_id: int):
        thirty_days_ago = date.today() - timedelta(days=30)
        query = select(cls.model).where(
            and_(
                cls.model.user_id == user_id,
                cls.model.recorded_at >= thirty_days_ago
            )
        ).order_by(cls.model.recorded_at)
        result = await session.execute(query)
        return result.scalars().all()
