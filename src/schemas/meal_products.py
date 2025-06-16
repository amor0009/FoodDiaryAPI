from uuid import UUID

from pydantic import BaseModel


class MealProductsRead(BaseModel):
    product_weight: float
    meal_id: UUID
    product_id: UUID

    class Config:
        from_attributes = True


class MealProductsUpdate(BaseModel):
    product_weight: float
    product_id: UUID


class MealProductsCreate(BaseModel):
    product_weight: float
    product_id: UUID
