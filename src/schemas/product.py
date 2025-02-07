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
    id: int
    name: Optional[str] = None
    weight: Optional[float] = None
    calories: Optional[float] = None
    proteins: Optional[float] = None
    fats: Optional[float] = None
    carbohydrates: Optional[float] = None
    description: Optional[str] = None
    picture_path: Optional[str] = None


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
