from typing import Optional
from pydantic import BaseModel, computed_field


class ProductRead(BaseModel):
    id: int
    name: str
    weight: float
    calories: float
    proteins: float
    fats: float
    carbohydrates: float
    description: Optional[str] = None
    has_picture: Optional[bool] = None

    @computed_field
    def picture(self) -> Optional[str]:
        return f"/product/picture/{self.id}" if self.has_picture else None

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
