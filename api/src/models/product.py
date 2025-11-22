from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey, Double, JSON
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from jinja2 import Template
from api.src.models.base import Base


if TYPE_CHECKING:
    from api.src.models.user import User
    from api.src.models.meal_products import MealProducts
    from api.src.models.brand import Brand


class Product(Base):
    __tablename__ = "product"

    slug: Mapped[str] = mapped_column(String(1200), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    weight: Mapped[float] = mapped_column(Double, nullable=False)
    calories: Mapped[float] = mapped_column(Double, nullable=False)
    proteins: Mapped[float] = mapped_column(Double, nullable=False)
    fats: Mapped[float] = mapped_column(Double, nullable=False)
    carbohydrates: Mapped[float] = mapped_column(Double, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    images: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user.id"),
        index=True
    )
    brand_id: Mapped[UUID] = mapped_column(ForeignKey("brands.id"), nullable=True)

    @hybrid_property
    def has_images(self):
        return self.images is not None

    user: Mapped["User"] = relationship("User", back_populates="products")
    brand: Mapped["Brand"] = relationship("Brand", back_populates="products")
    meal_products: Mapped[list["MealProducts"]] = relationship(
        "MealProducts",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    async def __admin_select2_repr__(self, request):
        return Template(
            "<span><strong>Название:</strong> {{obj.name}}</span>"
            "<span><strong>\tБренд:</strong> {{obj.brand.title if obj.brand else \"Нет\"}}</span>",
            autoescape=True,
        ).render(obj=self)

    def __str__(self):
        return f"Продукт: #{self.name}"
