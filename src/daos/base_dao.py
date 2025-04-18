from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession


class BaseDAO:
    model = None

    @classmethod
    async def find_by_id(cls, session: AsyncSession, model_id: int):
        query = select(cls.model).filter_by(id=model_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def find_one_or_none(cls, session: AsyncSession, options=None, **filter_by):
        query = select(cls.model).filter_by(**filter_by)
        if options:
            query = query.options(*options)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def find_all(
        cls,
        session: AsyncSession,
        offset: int | None = None,
        limit: int | None = None,
        order_by=None,
        **filter_by,
    ):
        query = select(cls.model).filter_by(**filter_by)
        if order_by is not None:
            query = query.order_by(order_by)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        result = await session.execute(query)
        return result.scalars().all()

    @classmethod
    async def add(cls, session: AsyncSession, **data):
        instance = cls.model(**data)
        session.add(instance)
        return instance

    @classmethod
    async def add_all(cls, session: AsyncSession, rows: list[dict]):
        instances = [cls.model(**row) for row in rows]
        session.add_all(instances)
        return instances

    @classmethod
    async def update(cls, session: AsyncSession, id: int, **data):
        data = {key: value for key, value in data.items() if value is not None}

        query = (
            update(cls.model)
            .filter_by(id=id)
            .values(**data)
            .returning(cls.model)
            .execution_options(synchronize_session="fetch")
        )
        result = await session.execute(query)

        updated_instance = result.scalar_one_or_none()
        if updated_instance:
            await session.refresh(updated_instance)
        return updated_instance

    @classmethod
    async def delete(cls, session: AsyncSession, **data):
        query = delete(cls.model).filter_by(**data)
        await session.execute(query)

    @classmethod
    async def truncate(cls, session: AsyncSession):
        table_name = cls.model.__table__.name
        query = text(f'TRUNCATE TABLE "{table_name}" CASCADE')
        await session.execute(query)

    @classmethod
    async def count(cls, session: AsyncSession, **filter_by):
        query = select(func.count()).select_from(cls.model).filter_by(**filter_by)
        result = await session.execute(query)
        return result.scalar()

    @classmethod
    async def exists(cls, session: AsyncSession, **filter_by):
        query = select(cls.model).filter_by(**filter_by).limit(1)
        result = await session.execute(query)
        return result.scalar() is not None
