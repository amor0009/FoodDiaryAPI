from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class UserWeightRead(BaseModel):
    id: UUID
    user_id: UUID
    weight: Optional[float] = None
    recorded_at: Optional[date] = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed=True


class UserWeightUpdate(BaseModel):
    weight: Optional[float] = None


class UserWeightCreate(BaseModel):
    weight: Optional[float] = None
