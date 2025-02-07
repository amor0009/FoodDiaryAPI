from typing import Optional
from pydantic import BaseModel


class UserRead(BaseModel):
    id: int
    login: str
    email: str
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    age: Optional[int] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    gender: Optional[str] = None
    activity_level: Optional[str] = None
    aim: Optional[str] = None
    recommended_calories: Optional[float] = None
    profile_image: Optional[str] = None

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
    weight: Optional[int] = None
    gender: Optional[str] = None
    activity_level: Optional[str] = None
    aim: Optional[str] = None
    recommended_calories: Optional[float] = None
    profile_image: Optional[str] = None


class UserCreate(BaseModel):
    login: str
    email: str
    password: str
