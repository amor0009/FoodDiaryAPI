from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, field_validator
from api.src.dependencies.repositories import get_object_repository


_object_repository = get_object_repository()


class ProductMedia(BaseModel):
    cover: str | None
    extra_media: list[str]

    @field_validator("cover")
    def validate_cover(cls, val):
        if val:
            return _object_repository.get_url(val)
        return val

    @field_validator("extra_media")
    def validate_extra_media(cls, val):
        if val:
            return [_object_repository.get_url(el) for el in val]
        return val


class ProductRead(BaseModel):
    id: UUID
    name: str
    weight: float
    calories: float
    proteins: float
    fats: float
    carbohydrates: float
    description: str | None = None
    has_images: bool | None = None
    images: ProductMedia | None = None
    is_public: bool
    user_id: UUID | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProductUpdate(BaseModel):
    name: str | None = None
    weight: float | None = None
    calories: float | None = None
    proteins: float | None = None
    fats: float | None = None
    carbohydrates: float | None = None
    description: str | None = None


class ProductCreate(BaseModel):
    name: str
    weight: float
    calories: float
    proteins: float
    fats: float
    carbohydrates: float
    description: str


class ProductAdd(BaseModel):
    name: str
    weight: float
