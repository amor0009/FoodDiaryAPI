from enum import Enum
from src.core.uuid_generator import UUIDGenerator
from src.database import Base
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID


class Staff(Base):
    __tablename__ = "staff"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=UUIDGenerator.generate_uuid)
    login = Column(String(50), nullable=False, unique=True)
    hashed_password = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)


class StaffRole(str, Enum):
    ADMIN = "admin"
    GENERAL_MANAGER = "general_manager"
    CONTENT_MANAGER = "content_manager"
    SUPPORT_MANAGER = "support_manager"
    MARKETING_SPECIALIST = "marketing_specialist"
    PRODUCT_MANAGER = "product_manager"
