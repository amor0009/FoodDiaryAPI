from datetime import date
from sqlalchemy import Column, Double, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from src.core.uuid_generator import UUIDGenerator
from src.database.database import Base


class UserWeight(Base):
    __tablename__ = 'user_weight'

    id = Column(UUID(as_uuid=True), primary_key=True, default=UUIDGenerator.generate_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), index=True, nullable=False)
    weight = Column(Double, nullable=False)
    recorded_at = Column(Date, nullable=False, default=date.today(), index=True)

    user = relationship("User", back_populates="recorded_weight")
