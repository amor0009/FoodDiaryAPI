from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Double
from sqlalchemy.orm import relationship
from src.database.database import Base


class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    weight = Column(Double, nullable=False)
    calories = Column(Double, nullable=False)
    proteins = Column(Double, nullable=False)
    fats = Column(Double, nullable=False)
    carbohydrates = Column(Double, nullable=False)
    description = Column(String, nullable=True)
    picture_path = Column(String, nullable=True)
    is_public = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    user = relationship("User", back_populates="products")
    meal_products = relationship("MealProducts", back_populates="product")
