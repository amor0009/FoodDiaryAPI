from uuid import UUID

from pydantic import BaseModel
from datetime import date


class StaffRead(BaseModel):
    id: UUID
    login: str
    role: str
    created_at: date

    class Config:
        from_attributes = True
