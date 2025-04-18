from src.daos.base_dao import BaseDAO
from src.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select


class AuthDAO(BaseDAO):
    model = User

    @classmethod
    # Поиск пользователя по логину или email
    async def find_by_login_or_email(
            cls,
            session: AsyncSession,
            login_or_email: str,
    ) -> User | None:
        query = select(cls.model).where(
            or_(
                cls.model.login == login_or_email,
                cls.model.email == login_or_email
            )
        )

        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    # Создание пользователя с хэшированным паролем
    async def create_with_hashed_password(
            cls,
            session: AsyncSession,
            login: str,
            email: str,
            hashed_password: str,
            commit: bool = True
    ) -> User:
        user = cls.model(
            login=login,
            email=email,
            hashed_password=hashed_password
        )

        session.add(user)
        if commit:
            await session.commit()
            await session.refresh(user)

        return user

    @classmethod
    # Проверка, есть ли пользователь с таким email
    async def email_exists(cls, session: AsyncSession, email: str) -> bool:
        return await cls.exists(session, email=email)

    @classmethod
    # Проверка, есть ли пользователь с таким логином
    async def login_exists(cls, session: AsyncSession, login: str) -> bool:
        return await cls.exists(session, login=login)

    @classmethod
    # Обновление пароля пользователя
    async def update_password(
            cls,
            session: AsyncSession,
            user_id: int,
            new_hashed_password: str
    ) -> User | None:
        return await cls.update(
            session,
            id=user_id,
            hashed_password=new_hashed_password
        )
