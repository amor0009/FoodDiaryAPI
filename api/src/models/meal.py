from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Double
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.src.models.base import Base


if TYPE_CHECKING:
    from api.src.models.user import User
    from api.src.models.meal_products import MealProducts


class Meal(Base):
    __tablename__ = "meal"

    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    weight: Mapped[float] = mapped_column(Double, nullable=False)
    calories: Mapped[float] = mapped_column(Double, nullable=False)
    proteins: Mapped[float] = mapped_column(Double, nullable=False)
    fats: Mapped[float] = mapped_column(Double, nullable=False)
    carbohydrates: Mapped[float] = mapped_column(Double, nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user.id"),
        index=True,
        nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="meals")
    meal_products: Mapped[list["MealProducts"]] = relationship(
        "MealProducts",
        back_populates="meal",
        cascade="all, delete-orphan"
    )
