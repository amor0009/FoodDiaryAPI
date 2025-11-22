from typing import TYPE_CHECKING
from sqlalchemy import Double, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.src.models.base import Base


if TYPE_CHECKING:
    from api.src.models.user import User


class UserWeight(Base):
    __tablename__ = 'user_weight'

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey('user.id'),
        index=True,
        nullable=False
    )
    weight: Mapped[float] = mapped_column(Double, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="recorded_weight")
