from sqlalchemy import Column, Integer, ForeignKey, Double
from sqlalchemy.orm import relationship
from src.database.database import Base


class MealProducts(Base):
    __tablename__ = "meal_products"

    product_weight = Column(Double, nullable=False)
    meal_id = Column(Integer, ForeignKey("meal.id"), primary_key=True)
    product_id = Column(Integer, ForeignKey("product.id"), primary_key=True)

    meal = relationship("Meal", back_populates="meal_products")
    product = relationship("Product", back_populates="meal_products")
