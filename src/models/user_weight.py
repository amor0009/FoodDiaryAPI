from datetime import date
from sqlalchemy import Column, Integer, Double, ForeignKey, Date
from sqlalchemy.orm import relationship
from src.database.database import Base


class UserWeight(Base):
    __tablename__ = 'user_weight'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    weight = Column(Double, nullable=False)
    recorded_at = Column(Date, nullable=False, default=date.today())

    user = relationship("User", back_populates="recorded_weight")
