from datetime import date
from uuid import UUID
from pydantic import BaseModel
from api.src.schemas.meal_products import MealProductsCreate, MealProductsUpdate
from api.src.schemas.product import ProductRead


class MealRead(BaseModel):
    id: UUID
    name: str
    weight: float
    calories: float
    proteins: float
    fats: float
    carbohydrates: float
    created_at: date
    user_id: UUID
    products: list[ProductRead] | None = None

    class Config:
        from_attributes = True

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "weight": self.weight,
            "calories": self.calories,
            "proteins": self.proteins,
            "fats": self.fats,
            "carbohydrates": self.carbohydrates,
            "created_at": self.created_at.isoformat(),
            "user_id": self.user_id,
            "products": [product.dict() for product in self.products] if self.products else []
        }


class MealUpdate(BaseModel):
    name: str
    products: list[MealProductsUpdate] | None = None


class MealCreate(BaseModel):
    name: str
    products: list[MealProductsCreate] | None = None
