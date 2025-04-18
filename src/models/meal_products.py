from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, ForeignKey, Double, UniqueConstraint
from sqlalchemy.orm import relationship
from src.core.uuid_generator import UUIDGenerator
from src.database.database import Base


class MealProducts(Base):
    __tablename__ = "meal_products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=UUIDGenerator.generate_uuid)
    product_weight = Column(Double, nullable=False)
    meal_id = Column(UUID(as_uuid=True), ForeignKey("meal.id"), index=True, nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("product.id"), index=True, nullable=False)

    __table_args__ = (
        UniqueConstraint('meal_id', 'product_id', name='uq_meal_product'),
    )

    meal = relationship("Meal", back_populates="meal_products")
    product = relationship("Product", back_populates="meal_products")
