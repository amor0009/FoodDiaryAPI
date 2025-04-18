from pydantic import BaseModel, Field


class Pagination(BaseModel):
    limit: int = Field(12, gt=0)
    offset: int = Field(0, ge=0)
