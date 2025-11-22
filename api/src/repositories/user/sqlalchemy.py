from dataclasses import dataclass
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, update
from api.src.models.user import User
from api.src.repositories.user.base import BaseUserRepository
from api.src.repositories.crud import CrudOperations


@dataclass(slots=True)
class SqlAlchemyUserRepository(BaseUserRepository):
    def __init__(self) -> None:
        self._crud = CrudOperations(User)

    async def find_by_email(self, session: AsyncSession, email: str) -> User | None:
        query = select(User).where(User.email == email)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def find_by_login_or_email(self, session: AsyncSession, login_or_email: str) -> User | None:
        query = select(User).where(
            or_(
                User.email == login_or_email,
                User.login == login_or_email
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def email_exists(self, session: AsyncSession, email: str) -> bool:
        return await self._crud.exists(session, email=email)

    async def create_user(
        self,
        session: AsyncSession,
        login: str,
        email: str,
        hashed_password: str
    ) -> User:
        user = User(
            login=login,
            email=email,
            hashed_password=hashed_password
        )
        return await self._crud.insert(session, user)

    async def get_by_id(self, session: AsyncSession, user_id: UUID) -> User | None:
        return await self._crud.get_by_id(session, user_id)

    async def update_user(
        self,
        session: AsyncSession,
        user: User,
        update_data: dict
    ) -> User:
        for key, value in update_data.items():
            setattr(user, key, value)
        await session.commit()
        await session.refresh(user)
        return user

    async def update_profile_images(
        self,
        session: AsyncSession,
        user: User,
        images_data: dict
    ) -> User:
        user.images = images_data
        await session.commit()
        await session.refresh(user)
        return user

    async def delete(self, session: AsyncSession, user_id: UUID) -> None:
        await self._crud.delete(session, user_id)

    async def update_email(
        self, session: AsyncSession, user_id: UUID, email: str
    ) -> User:
        query = (
            update(User).where(User.id == user_id).values(email=email, login=email).returning(User)
        )
        result = await session.execute(query)
        await session.flush()
        return result.scalar_one()

    async def update_password(
        self, session: AsyncSession, user_id: UUID, hashed_password: bytes
    ) -> User:
        query = (
            update(User)
            .where(User.id == user_id)
            .values(hashed_password=hashed_password)
            .returning(User)
        )
        result = await session.execute(query)
        return result.scalar_one()
