from collections.abc import Sequence
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo
import anyio.to_thread
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette_admin.contrib.sqla import ModelView as BModelView


class ModelView(BModelView):
    async def edit(self, request: Request, pk: Any, data: dict[str, Any]) -> Any:
        try:
            data = await self._arrange_data(request, data, True)
            await self.validate(request, data)
            session: Session | AsyncSession = request.state.session
            obj = await self.find_by_pk(request, pk)
            await self._populate_obj(request, obj, data, True)
            session.add(obj)
            await self.before_edit(request, data, obj)
            if isinstance(session, AsyncSession):
                await session.commit()
                await session.refresh(obj)
            else:
                await anyio.to_thread.run_sync(session.commit)
                await anyio.to_thread.run_sync(session.refresh, obj)
            await self.after_edit(request, obj)
            return obj
        except Exception as e:
            self.handle_exception(e)

    async def find_all(
        self,
        request: Request,
        skip: int = 0,
        limit: int = 100,
        where: dict[str, Any] | str | None = None,
        order_by: list[str] | None = None,
    ) -> Sequence[Any]:
        processed_where = where
        if where is not None:
            processed_where = convert_datetimes(where)

        return await super().find_all(
            request=request,
            skip=skip,
            limit=limit,
            where=processed_where,
            order_by=order_by,
        )

    async def count(self, request: Request, where: dict[str, Any] | str | None = None) -> int:
        processed_where = where
        if where is not None:
            processed_where = convert_datetimes(where)
        return await super().count(request=request, where=processed_where)


def convert_datetimes(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: convert_datetimes(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_datetimes(item) for item in data]
    elif isinstance(data, str):
        try:
            dt_obj = datetime.fromisoformat(data).replace(tzinfo=ZoneInfo("Europe/Moscow"))
            dt_obj = dt_obj.astimezone(ZoneInfo("UTC"))
            return dt_obj.replace(tzinfo=None)
        except ValueError:
            return data
    return data


class DateTimeBModelView(BModelView):
    async def find_all(
        self,
        request: Request,
        skip: int = 0,
        limit: int = 100,
        where: dict[str, Any] | str | None = None,
        order_by: list[str] | None = None,
    ) -> Sequence[Any]:
        processed_where = where
        if where is not None:
            processed_where = convert_datetimes(where)

        return await super().find_all(
            request=request,
            skip=skip,
            limit=limit,
            where=processed_where,
            order_by=order_by,
        )

    async def count(self, request: Request, where: dict[str, Any] | str | None = None) -> int:
        processed_where = where
        if where is not None:
            processed_where = convert_datetimes(where)
        return await super().count(request=request, where=processed_where)


class SecuredModelView(ModelView):

    def is_accessible(self, request: Request) -> bool:
        return True

    def can_view(self, request: Request) -> bool:
        return self.is_accessible(request)

    def can_create(self, request: Request) -> bool:
        return self.is_accessible(request)

    def can_edit(self, request: Request) -> bool:
        return self.is_accessible(request)

    def can_delete(self, request: Request) -> bool:
        return self.is_accessible(request)
