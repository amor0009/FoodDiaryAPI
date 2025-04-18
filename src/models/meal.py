from datetime import date
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Double, DateTime
from sqlalchemy.orm import relationship
from src.database.database import Base


class Meal(Base):
    __tablename__ = "meal"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    weight = Column(Double, nullable=False)
    calories = Column(Double, nullable=False)
    proteins = Column(Double, nullable=False)
    fats = Column(Double, nullable=False)
    carbohydrates = Column(Double, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"))
    recorded_at = Column(Date, default=date.today(), nullable=False)

    user = relationship("User", back_populates="meals")
    meal_products = relationship("MealProducts", back_populates="meal")
