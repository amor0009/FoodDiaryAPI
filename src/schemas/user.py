from typing import Optional
from pydantic import BaseModel, computed_field


class UserRead(BaseModel):
    id: int
    login: str
    email: str
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    age: Optional[int] = None
    height: Optional[int] = None
    weight: Optional[float] = None
    gender: Optional[str] = None
    activity_level: Optional[str] = None
    aim: Optional[str] = None
    recommended_calories: Optional[float] = None
    has_profile_picture: Optional[bool] = None

    @computed_field
    def profile_picture(self) -> Optional[str]:
        return f"/user/profile-picture/{self.id}" if self.has_profile_picture else None

    class Config:
        from_attributes = True


class UserCalculateNutrients(BaseModel):
    age: Optional[int] = None
    height: Optional[int] = None
    weight: Optional[float] = None
    gender: Optional[str] = None
    activity_level: Optional[str] = None
    aim: Optional[str] = None
    target_weight: Optional[float] = None
    target_days: Optional[int] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    login: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    age: Optional[int] = None
    height: Optional[int] = None
    weight: Optional[float] = None
    gender: Optional[str] = None
    activity_level: Optional[str] = None
    aim: Optional[str] = None
    recommended_calories: Optional[float] = None


class UserCreate(BaseModel):
    login: str
    email: str
    password: str


class UserAuth(BaseModel):
    username: str  # login или email
    password: str
