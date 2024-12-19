from typing import Optional
from pydantic import BaseModel


class ProductRead(BaseModel):
    id: int
    name: str
    weight: float
    calories: float
    proteins: float
    fats: float
    carbohydrates: float
    description: Optional[str] = None
    picture_path: Optional[str] = None

    class Config:
        from_attributes = True


class ProductUpdate(BaseModel):
    name: str
    weight: float
    calories: float
    proteins: float
    fats: float
    carbohydrates: float
    description: str
    picture_path: str


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
