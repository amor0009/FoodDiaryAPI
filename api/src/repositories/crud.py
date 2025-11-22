from dataclasses import dataclass
from typing import Type, TypeVar, Generic
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, update
from api.src.models.base import Base


ModelType = TypeVar("ModelType", bound=Base)


@dataclass(slots=True)
class CrudOperations(Generic[ModelType]):
    model: Type[ModelType]

    async def get_by_id(self, session: AsyncSession, obj_id: UUID) -> ModelType | None:
        query = select(self.model).where(self.model.id == obj_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        session: AsyncSession,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[ModelType]:
        query = select(self.model)

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        result = await session.execute(query)
        return list(result.scalars())

    async def insert(self, session: AsyncSession, obj_instance: ModelType) -> ModelType:
        session.add(obj_instance)
        return obj_instance

    async def delete(self, session: AsyncSession, obj_id: UUID) -> None:
        query = delete(self.model).where(self.model.id == obj_id)
        await session.execute(query)

    async def update(self, session: AsyncSession, obj_id: UUID, **values) -> ModelType | None:
        stmt = (
            update(self.model)
            .where(self.model.id == obj_id)
            .values(**values)
            .returning(self.model)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists(self, session: AsyncSession, **filters) -> bool:
        query = select(select(self.model).where(*[getattr(self.model, key) == value for key, value in filters.items()]).exists())
        result = await session.execute(query)
        return result.scalar_one()
