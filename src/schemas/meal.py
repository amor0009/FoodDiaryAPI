from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from src.schemas.meal_products import MealProductsCreate, MealProductsUpdate
from src.schemas.product import ProductRead


class MealRead(BaseModel):
    id: int
    name: str
    weight: float
    calories: float
    proteins: float
    fats: float
    carbohydrates: float
    date: datetime
    user_id: int
    products: Optional[List[ProductRead]] = []

    class Config:
        from_attributes = True


class MealUpdate(BaseModel):
    name: str
    weight: float
    calories: float
    proteins: float
    fats: float
    carbohydrates: float
    products: Optional[List[MealProductsUpdate]] = []


class MealCreate(BaseModel):
    name: str
    weight: float
    calories: float
    proteins: float
    fats: float
    carbohydrates: float
    products: Optional[List[MealProductsCreate]] = []

