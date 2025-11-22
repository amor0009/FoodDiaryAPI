from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class UserWeightRead(BaseModel):
    id: UUID
    user_id: UUID
    weight: float | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class UserWeightUpdate(BaseModel):
    weight: float | None = None


class UserWeightCreate(BaseModel):
    weight: float | None = None
