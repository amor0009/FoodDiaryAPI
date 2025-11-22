from enum import Enum
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, Double, Boolean
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column
from api.src.models.base import Base


if TYPE_CHECKING:
    from api.src.models.meal import Meal
    from api.src.models.product import Product
    from api.src.models.user_weight import UserWeight


class GenderEnum(str, Enum):
    MALE = "male"
    FEMALE = "female"

    @classmethod
    def get_admin_choices(cls):
        return [
            (cls.MALE.value, "Мужской"),
            (cls.FEMALE.value, "Женский"),
        ]


class AimEnum(str, Enum):
    LOSS = "loss"
    MAINTAIN = "maintain"
    GAIN = "gain"

    @classmethod
    def get_admin_choices(cls):
        return [
            (cls.LOSS.value, "Похудение"),
            (cls.MAINTAIN.value, "Поддержание веса"),
            (cls.GAIN.value, "Набор массы"),
        ]


class ActivityLevelEnum(str, Enum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    ACTIVE = "active"
    VERY_ACTIVE = "very_active"

    @classmethod
    def get_admin_choices(cls):
        return [
            (cls.SEDENTARY.value, "Сидячий образ жизни"),
            (cls.LIGHT.value, "Легкая активность"),
            (cls.MODERATE.value, "Умеренная активность"),
            (cls.ACTIVE.value, "Активный образ жизни"),
            (cls.VERY_ACTIVE.value, "Очень активный образ жизни"),
        ]


class User(Base):
    __tablename__ = "user"

    login: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    firstname: Mapped[str | None] = mapped_column(String, nullable=True)
    lastname: Mapped[str | None] = mapped_column(String, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[float | None] = mapped_column(Double, nullable=True)
    gender: Mapped[GenderEnum | None] = mapped_column(SQLEnum(GenderEnum), nullable=True)
    aim: Mapped[AimEnum | None] = mapped_column(SQLEnum(AimEnum), nullable=True)
    activity_level: Mapped[ActivityLevelEnum | None] = mapped_column(SQLEnum(ActivityLevelEnum), nullable=True)
    recommended_calories: Mapped[float | None] = mapped_column(Double, nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(75), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @hybrid_property
    def has_avatar(self):
        return self.avatar is not None

    meals: Mapped[list["Meal"]] = relationship("Meal", back_populates="user", cascade="all, delete-orphan")
    products: Mapped[list["Product"]] = relationship("Product", back_populates="user", cascade="all, delete-orphan")
    recorded_weight: Mapped[list["UserWeight"]] = relationship("UserWeight", back_populates="user", cascade="all, delete-orphan")

    def __str__(self):
        return f"Пользователь: {self.email}"
