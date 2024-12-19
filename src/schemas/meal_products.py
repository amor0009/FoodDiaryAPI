from typing import List
from pydantic import BaseModel


class MealProductsRead(BaseModel):
    product_weight: float
    meal_id: int
    products_id: List[int]
    class Config:
        from_attributes = True


class MealProductsUpdate(BaseModel):
    product_weight: float
    product_id: int


class MealProductsCreate(BaseModel):
    product_weight: float
    product_id: int