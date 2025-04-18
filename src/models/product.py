from sqlalchemy import Column, String, Boolean, ForeignKey, Double, LargeBinary
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.dialects.postgresql import UUID
from src.core.uuid_generator import UUIDGenerator
from src.database.database import Base


class Product(Base):
    __tablename__ = "product"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=UUIDGenerator.generate_uuid)
    name = Column(String(100), unique=True, index=True, nullable=False)
    weight = Column(Double, nullable=False)
    calories = Column(Double, nullable=False)
    proteins = Column(Double, nullable=False)
    fats = Column(Double, nullable=False)
    carbohydrates = Column(Double, nullable=False)
    description = Column(String, nullable=True)
    picture = Column(LargeBinary, nullable=True)
    is_public = Column(Boolean, default=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), index=True)

    @hybrid_property
    def has_picture(self):
        return self.picture is not None

    has_picture = column_property(picture.isnot(None))

    user = relationship("User", back_populates="products")
    meal_products = relationship("MealProducts", back_populates="product", cascade="all, delete-orphan")
