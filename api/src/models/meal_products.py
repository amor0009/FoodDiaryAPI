from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Double, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.src.models.base import Base


if TYPE_CHECKING:
    from api.src.models.meal import Meal
    from api.src.models.product import Product


class MealProducts(Base):
    __tablename__ = "meal_products"

    product_weight: Mapped[float] = mapped_column(Double, nullable=False)
    meal_id: Mapped[UUID] = mapped_column(
        ForeignKey("meal.id"),
        index=True,
        nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("product.id"),
        index=True,
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint('meal_id', 'product_id', name='uq_meal_product'),
    )

    meal: Mapped["Meal"] = relationship("Meal", back_populates="meal_products")
    product: Mapped["Product"] = relationship("Product", back_populates="meal_products")