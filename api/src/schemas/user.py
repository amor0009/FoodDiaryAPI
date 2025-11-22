from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, model_validator, field_validator
from api.src.models.user import GenderEnum, ActivityLevelEnum, AimEnum
from api.src.dependencies.repositories import get_object_repository


_object_repository = get_object_repository()


class UserAvatar(BaseModel):
    avatar: str | None

    @field_validator("avatar")
    def validate_avatar(cls, val):
        if val:
            return _object_repository.get_url(val)
        return val


class UserRead(BaseModel):
    id: UUID
    email: str
    firstname: str | None = None
    lastname: str | None = None
    age: int | None = None
    height: int | None = None
    weight: float | None = None
    gender: GenderEnum | None = None
    activity_level: ActivityLevelEnum | None = None
    aim: AimEnum | None = None
    recommended_calories: float | None = None
    has_avatar: bool = False
    avatar: UserAvatar | None = None

    class Config:
        from_attributes = True


class UserCalculateNutrients(BaseModel):
    age: int | None = None
    height: int | None = None
    weight: float | None = None
    gender: GenderEnum | None = None
    activity_level: ActivityLevelEnum | None = None
    aim: AimEnum | None = None
    target_weight: float | None = None
    target_days: int | None = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    firstname: str | None = None
    lastname: str | None = None
    age: int | None = None
    height: int | None = None
    weight: float | None = None
    gender: GenderEnum | None = None
    activity_level: ActivityLevelEnum | None = None
    aim: AimEnum | None = None


class RegisterUser(BaseModel):
    email: EmailStr = Field(..., description="Email для регистрации")


class CheckRegistrationUser(BaseModel):
    email: EmailStr = Field(..., description="Email для проверки кода")
    code: str = Field(..., description="Код подтверждения")


class CreateUser(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=6, description="Пароль")
    password_confirm: str = Field(..., description="Подтверждение пароля")
    code: str = Field(..., description="Код подтверждения")
    firstname: str | None = Field(None, description="Имя")
    lastname: str | None = Field(None, description="Фамилия")

    @model_validator(mode='before')
    @classmethod
    def check_passwords_match(cls, values):
        password = values.get('password')
        password_confirm = values.get('password_confirm')

        if password != password_confirm:
            raise ValueError('Пароли не совпадают')
        return values


class UserAuth(BaseModel):
    username: str
    password: str


class EmailChangeConfirm(BaseModel):
    email: EmailStr
    code: str


class StartForgotPassword(BaseModel):
    email: EmailStr


class CheckForgotPassword(BaseModel):
    code: str


class UpdateForgotPassword(BaseModel):
    new_password: str
    password_confirm: str
    code: str


class UpdatePassword(BaseModel):
    old_password: str
    new_password: str
    password_confirm: str
