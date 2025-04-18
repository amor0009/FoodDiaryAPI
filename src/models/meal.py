from datetime import date
from sqlalchemy import Column, String, ForeignKey, Date, Double
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from src.core.uuid_generator import UUIDGenerator
from src.database.database import Base


class Meal(Base):
    __tablename__ = "meal"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=UUIDGenerator.generate_uuid)
    name = Column(String, index=True, nullable=False)
    weight = Column(Double, nullable=False)
    calories = Column(Double, nullable=False)
    proteins = Column(Double, nullable=False)
    fats = Column(Double, nullable=False)
    carbohydrates = Column(Double, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), index=True, nullable=False)
    recorded_at = Column(Date, default=date.today(), nullable=False)

    user = relationship("User", back_populates="meals")
    meal_products = relationship("MealProducts", back_populates="meal", cascade="all, delete-orphan")
