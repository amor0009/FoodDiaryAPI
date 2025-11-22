from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import relationship, Mapped, mapped_column
from jinja2 import Template
from api.src.models.base import Base


if TYPE_CHECKING:
    from api.src.models.product import Product


class Brand(Base):
    __tablename__ = "brands"

    title: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    products: Mapped[list["Product"]] = relationship(back_populates="brand")

    async def __admin_select2_repr__(self, request):
        return Template(
            "<span><strong>Бренд:</strong> {{obj.title}} </span>",
            autoescape=True,
        ).render(obj=self)

    async def __admin_repr__(self, request):
        return self.title
