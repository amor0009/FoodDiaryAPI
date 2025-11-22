from collections.abc import Sequence
from datetime import UTC
from typing import Any
from zoneinfo import ZoneInfo

from starlette_admin import (
    BaseField,
    CollectionField,
    DateTimeField,
    FileField,
    ImageField,
    StringField,
    RequestAction,
)
from starlette_admin.helpers import html_params
from starlette.requests import Request

from api.src.dependencies.repositories import get_object_repository
from api.src.repositories.objects.base import BaseObjectRepository


class SingleImageField(ImageField):
    _object_repository: BaseObjectRepository = get_object_repository()

    async def serialize_value(self, request: Request, value: str, action: RequestAction) -> Any:
        if not value:
            return None

        try:
            if action == RequestAction.LIST:
                return self._object_repository.get_url(value)
            else:
                return {
                    "url": self._object_repository.get_url(value),
                    "filename": value,
                    "exists": await self._object_repository.is_exist(value)
                }
        except Exception as e:
            return None

    async def parse_value(self, request: Request, value: Any) -> Any:
        if not value:
            return None

        if isinstance(value, list) and value:
            return value[0]

        return value


class ProductsFiles(FileField):
    _object_repository: BaseObjectRepository = get_object_repository()

    async def serialize_value(self, request, value, action):
        if not value:
            return []
        return [{"url": self._object_repository.get_url(file), "filename": file} for file in value]

    async def parse_obj(self, request, obj):
        return getattr(obj, 'images', {}).get('extra_media', [])


class MoscowDateTimeField(DateTimeField):
    async def serialize_value(self, request: Request, value: Any, action: RequestAction) -> Any:
        if not value.tzinfo:
            value = value.replace(tzinfo=UTC)
        moscow_datetime = value.astimezone(ZoneInfo("Europe/Moscow"))
        return await super().serialize_value(request, moscow_datetime, action)


class ProductCoverField(ImageField):
    _object_repository: BaseObjectRepository = get_object_repository()

    async def serialize_value(self, request: Request, value: dict, action: RequestAction) -> Any:
        if not value or not value.get("cover"):
            return None
        cover_filename = value["cover"]
        return {
            "url": self._object_repository.get_url(cover_filename),
            "filename": cover_filename,
        }

    async def parse_obj(self, request: Request, obj: Any) -> Any:
        return obj.images


class SlugTargetField(StringField):
    model: str

    def __init__(self, name: str, model: str, **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.model = model

    def input_params(self) -> str:
        parent_params_str = super().input_params()
        custom_params_dict = {"data-slug-target": "true"}
        return f"{parent_params_str} {html_params(custom_params_dict)}".strip()

    def get_model(self) -> str:
        return self.model
