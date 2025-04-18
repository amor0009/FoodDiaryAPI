from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.daos.base_dao import BaseDAO
from src.models.user import User


class UserDAO(BaseDAO):
    model = User

    @classmethod
    async def find_by_login_or_email(cls, session: AsyncSession, login_or_email: str):
        query = select(cls.model).where(
            or_(cls.model.login == login_or_email, cls.model.email == login_or_email)
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def update_user(
        cls,
        session: AsyncSession,
        user: User,
        update_data: dict
    ):
        for key, value in update_data.items():
            setattr(user, key, value)
        await session.commit()
        await session.refresh(user)
        return user

    @classmethod
    async def update_profile_picture(
        cls,
        session: AsyncSession,
        user: User,
        picture_data: bytes
    ):
        user.profile_picture = picture_data
        await session.commit()
        await session.refresh(user)
        return user
