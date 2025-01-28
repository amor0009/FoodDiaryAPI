from pydantic import BaseModel
from src.schemas.meal import MealRead
from src.schemas.product import ProductRead
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.schemas.meal import MealRead  # Используем TYPE_CHECKING

class MealProductsRead(BaseModel):
    product_weight: float
    meal_id: int
    product_id: int

    class Config:
        from_attributes = True

class MealProductsUpdate(BaseModel):
    product_weight: float
    product_id: int

class MealProductsCreate(BaseModel):
    product_weight: float
    product_id: int