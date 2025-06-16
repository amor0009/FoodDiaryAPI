from starlette_admin.contrib.sqla import ModelView
from starlette_admin.fields import (
    StringField,
    EmailField,
    DateTimeField,
    BooleanField,
    IntegerField,
    DateField,
    HasMany,
    HasOne,
    FileField,
    TextAreaField,
    NumberField
)
from starlette.requests import Request

from src.core.security import Security
from src.models.product import Product
from src.models.staff import Staff
from starlette_admin.exceptions import FormValidationError

from src.models.user import User


class StaffView(ModelView):
    def __init__(self):
        super().__init__(
            model=Staff,
            name="Staff",
            icon="fa-solid fa-user-tie",
            label="Staff"
        )

    fields = [
        "id",
        StringField("login", label="Логин", required=True, maxlength=50),
        StringField("role", label="Роль", required=True),
        DateTimeField("created_at", label="Дата создания", read_only=True),
    ]

    exclude_fields_from_list = ["hashed_password"]
    exclude_fields_from_create = ["created_at"]
    exclude_fields_from_edit = ["created_at", "hashed_password"]

    async def before_create(self, request: Request, data: dict, obj: Staff) -> None:
        if not data.get("password"):
            raise FormValidationError({"password": "Пароль обязателен"})
        obj.hashed_password = Security.get_password_hash(data["password"])

    async def before_edit(self, request: Request, data: dict, obj: Staff) -> None:
        if data.get("password"):
            obj.hashed_password = Security.get_password_hash(data["password"])


class UserView(ModelView):
    def __init__(self):
        super().__init__(
            model=User,
            name="Users",
            icon="fa-solid fa-user",
            label="User"
        )

        self.can_edit = lambda r: False
        self.can_delete = lambda r: False

    fields = [
        "id",
        StringField("login", label="Логин", required=True, maxlength=50),
        EmailField("email", label="Email", maxlength=255),
        StringField("firstname", label="Имя", maxlength=50),
        StringField("lastname", label="Фамилия", maxlength=50),
        IntegerField("age", label="Возраст"),
        FileField(
            "profile_picture",
            label="Аватар",
            required=False,
            # allowed_types=["image/jpeg", "image/png"]
        ),
        BooleanField("has_profile_picture", label="Есть аватар"),
        DateTimeField("registered_at", label="Дата регистрации", read_only=True),
    ]

    exclude_fields_from_create = ["registered_at", "has_profile_picture"]
    exclude_fields_from_edit = ["registered_at"]
    exclude_fields_from_list = ["hashed_password", "profile_picture"]

    async def before_create(self, request: Request, data: dict, obj: User) -> None:
        if not data.get("password"):
            raise FormValidationError({"password": "Пароль обязателен"})
        obj.hashed_password = Security.get_password_hash(data["password"])


class ProductView(ModelView):
    def __init__(self):
        super().__init__(
            model=Product,
            name="Products",
            icon="fa-solid fa-boxes-stacked",
            label="Product"
        )

    fields = [
        "id",
        StringField("name", label="Название", required=True, maxlength=100),
        NumberField("weight", label="Вес (г)", required=True),
        NumberField("calories", label="Калории (ккал)", required=True),
        NumberField("proteins", label="Белки (г)", required=True),
        NumberField("fats", label="Жиры (г)", required=True),
        NumberField("carbohydrates", label="Углеводы (г)", required=True),
        TextAreaField("description", label="Описание"),
        FileField(
            "picture",
            label="Изображение",
            required=False,
            #allowed_types=["image/jpeg", "image/png"]
        ),
        BooleanField("is_public", label="Публичный"),
        DateTimeField("created_at", label="Дата создания", read_only=True),
        HasOne("user", label="Создатель", identity="user", read_only=True),
        HasMany("meal_products", label="Приёмы пищи", identity="meal_product"),
    ]

    exclude_fields_from_create = ["created_at", "user"]
    exclude_fields_from_edit = ["user"]
    exclude_fields_from_list = ["picture", "meal_products"]
