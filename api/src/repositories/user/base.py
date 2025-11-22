from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models.user import User


class BaseUserRepository(ABC):
    @abstractmethod
    async def find_by_email(self, session: AsyncSession, email: str) -> User | None: ...

    @abstractmethod
    async def find_by_login_or_email(self, session: AsyncSession, login_or_email: str) -> User | None: ...

    @abstractmethod
    async def email_exists(self, session: AsyncSession, email: str) -> bool: ...

    @abstractmethod
    async def create_user(
        self,
        session: AsyncSession,
        login: str,
        email: str,
        hashed_password: str
    ) -> User: ...

    @abstractmethod
    async def get_by_id(self, session: AsyncSession, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def update_user(
        self,
        session: AsyncSession,
        user: User,
        update_data: dict
    ) -> User: ...

    @abstractmethod
    async def update_profile_images(
        self,
        session: AsyncSession,
        user: User,
        images_data: dict
    ) -> User: ...

    @abstractmethod
    async def delete(self, session: AsyncSession, user_id: UUID) -> None: ...

    @abstractmethod
    async def update_email(
        self, session: AsyncSession, user_id: UUID, email: str
    ) -> User: ...

    @abstractmethod
    async def update_password(
        self, session: AsyncSession, user_id: UUID, hashed_password: bytes
    ) -> User: ...
