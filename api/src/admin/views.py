from starlette_admin.fields import (
    EmailField,
    BooleanField,
    IntegerField,
    HasMany,
    TextAreaField,
    FloatField,
    EnumField,
)

from api.src.admin.fields import SingleImageField, MoscowDateTimeField, SlugTargetField, ProductCoverField, ProductsFiles
from api.src.admin.mixins import MixinImageControl
from api.src.admin.model_view import ModelView, SecuredModelView
from api.src.core.security import Security
from api.src.models.product import Product
from api.src.models.staff import PermissionsEnum, Role, Permission
from api.src.models.user import User, ActivityLevelEnum, AimEnum, GenderEnum
from typing import Any
from sqlalchemy import select
from starlette.requests import Request
from starlette_admin import StringField, PasswordField, HasOne
from starlette_admin.exceptions import FormValidationError
from api.src.models import Staff, Brand
from api.src.database.database import async_session_maker
from api.src.repositories.objects.base import BaseObjectRepository
from api.src.utils.common import generate_unique_slug
from api.src.utils.utils import is_valid_email


class StaffView(ModelView):
    name = "сотрудники"
    icon = "fa-solid fa-user-tie"
    label = "Сотрудники"

    permission_view = PermissionsEnum.STAFF_VIEW
    permission_create = PermissionsEnum.STAFF_CREATE
    permission_edit = PermissionsEnum.STAFF_EDIT
    permission_delete = PermissionsEnum.STAFF_DELETE

    list_template = "clickable_raw.html"

    def __init__(self):
        super().__init__(
            model=Staff,
            name="Сотрудники",
            icon="fa-solid fa-user-tie",
            label="Сотрудники"
        )

    fields = [
        StringField(
            "name",
            label="ФИО",
            required=True,
            maxlength=150,
        ),
        StringField(
            "login",
            label="Логин/Почта",
            required=True,
            maxlength=50,
        ),
        StringField(
            "email",
            label="Почта",
            required=True,
            maxlength=256,
        ),
        HasOne("role", label="Роль", identity="role", required=True),
        PasswordField("password", label="Пароль", required=True),
        MoscowDateTimeField("created_at", label="Дата создания", read_only=True),
        MoscowDateTimeField("updated_at", label="Дата обновления", read_only=True),
    ]

    exclude_fields_from_list = ["hashed_password", "password"]
    exclude_fields_from_detail = ["hashed_password"]
    exclude_fields_from_create = ["id", "created_at", "email", "updated_at"]
    exclude_fields_from_edit = ["id", "created_at", "hashed_password", "email", "updated_at"]

    async def _check_login_exists(self, login: str, exclude_id: str = None) -> bool:
        async with async_session_maker() as session:
            stmt = select(Staff).where(Staff.login == login)
            if exclude_id:
                stmt = stmt.where(Staff.id != exclude_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def before_create(self, request: Request, data: dict[str, Any], obj: Staff) -> None:
        password = data.get("password")
        if not password:
            raise FormValidationError({"password": "Пароль не может быть пустым"})

        name = data.get("name")
        if not name or len(name.strip().split()) != 3:
            raise FormValidationError({"name": "ФИО должно состоять из трёх слов"})

        login = data.get("login")
        if not is_valid_email(login):
            raise FormValidationError({"login": "Логин должен быть валидным email адресом"})

        if await self._check_login_exists(login):
            raise FormValidationError({"login": "Пользователь с таким логином уже существует"})

        obj.email = login

        if not data.get("role"):
            raise FormValidationError({"role": "Роль обязательна для заполнения"})

        obj.hashed_password = Security.get_password_hash(password)

    async def before_edit(
            self,
            request: Request,
            data: dict[str, Any],
            obj: Staff,
    ) -> None:
        password = data.get("password")
        if password:
            obj.hashed_password = Security.get_password_hash(password)

        name = data.get("name")
        if name and len(name.strip().split()) != 3:
            raise FormValidationError({"name": "ФИО должно состоять из трёх слов"})

        if not data.get("role"):
            raise FormValidationError({"role": "Роль обязательна для заполнения"})

        new_login = data.get("login")
        if obj.login != new_login:
            if not is_valid_email(new_login):
                raise FormValidationError({"login": "Логин должен быть валидным email адресом"})

            if await self._check_login_exists(new_login, str(obj.id)):
                raise FormValidationError({"login": "Пользователь с таким логином уже существует"})

            obj.login = new_login
            obj.email = new_login

    async def edit(self, request: Request, pk: Any, data: dict[str, Any]) -> Any:
        async with async_session_maker() as session:
            stmt = select(Staff).where(Staff.id == pk)
            result = await session.execute(stmt)
            obj = result.scalar_one_or_none()

            if obj is None:
                raise ValueError(f"Staff with id {pk} not found")

            await self.before_edit(request, data, obj)

            if "name" in data:
                obj.name = data["name"]
            if "login" in data:
                obj.login = data["login"]
                obj.email = data["login"]
            if "role" in data:
                obj.role_id = data["role"]

            await session.commit()
            await session.refresh(obj)
            return obj

    async def create(self, request: Request, data: dict[str, Any]) -> Any:
        obj = self.model()

        await self.before_create(request, data, obj)

        obj.name = data.get("name")
        obj.login = data.get("login")
        obj.email = data.get("login")
        obj.role_id = data.get("role")

        async with async_session_maker() as session:
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return obj

    async def serialize(
            self,
            obj: Any,
            request: Request,
            action: str = None,
            include_relationships: bool = True,
            **kwargs,
    ) -> dict[str, Any]:
        data = await super().serialize(obj, request, action, include_relationships, **kwargs)
        return data


class RoleView(SecuredModelView):
    name = "роли"
    icon = "fa-solid fa-user-shield"
    label = "Роли"

    permission_view = PermissionsEnum.ROLES_VIEW
    permission_create = PermissionsEnum.ROLES_CREATE
    permission_edit = PermissionsEnum.ROLES_EDIT
    permission_delete = PermissionsEnum.ROLES_DELETE

    list_template = "clickable_raw.html"

    def __init__(self):
        super().__init__(
            model=Role,
            name="роли",
            icon="fa-solid fa-user-shield",
            label="Роли"
        )

    fields = [
        "id",
        StringField("title", label="Название", required=True),
        HasMany("permissions", label="Права доступа", identity="permission", required=True),
        MoscowDateTimeField("created_at", label="Дата создания", read_only=True),
        MoscowDateTimeField("updated_at", label="Дата обновления", read_only=True),
    ]

    exclude_fields_from_create = ["id", "created_at", "updated_at"]
    exclude_fields_from_edit = ["id", "created_at", "updated_at"]

    searchable_fields = ["title"]
    sortable_fields = ["title"]
    fields_default_sort = ("title", "asc")

    async def before_create(self, request: Request, data: dict[str, Any], obj: Role) -> None:
        if not data.get("permissions"):
            raise FormValidationError({"permissions": "Права доступа обязательны для заполнения"})

    async def before_edit(
        self,
        request: Request,
        data: dict[str, Any],
        obj: Role,
    ) -> None:
        if not data.get("permissions"):
            raise FormValidationError({"permissions": "Права доступа обязательны для заполнения"})


class PermissionView(SecuredModelView):
    name = "права"
    icon = "fa-solid fa-key"
    label = "Права доступа"

    permission_view = PermissionsEnum.PERMISSIONS_VIEW

    list_template = "clickable_raw.html"

    def __init__(self):
        super().__init__(
            model=Permission,
            name="права",
            icon="fa-solid fa-key",
            label="Права доступа"
        )

    fields = [
        "id",
        StringField("title", label="Название", required=True),
        TextAreaField("description", label="Описание", required=True),
        MoscowDateTimeField("created_at", label="Дата создания", read_only=True),
        MoscowDateTimeField("updated_at", label="Дата обновления", read_only=True),
    ]

    exclude_fields_from_create = ["id", "created_at", "updated_at"]
    exclude_fields_from_edit = ["id", "created_at", "updated_at"]

    sortable_fields = ["title"]
    fields_default_sort = ("title", "asc")

    def can_create(self, request: Request) -> bool:
        return False

    def can_delete(self, request: Request) -> bool:
        return False

    def can_edit(self, request: Request) -> bool:
        return False


class UserView(ModelView, MixinImageControl):
    def __init__(
        self,
        object_repository: BaseObjectRepository,
    ):
        self._object_repository = object_repository
        super().__init__(
            model=User,
            name="пользователя",
            icon="fa-solid fa-user",
            label="Пользователи"
        )

    list_template = "clickable_raw.html"

    fields = [
        "id",
        EmailField("login", label="Логин/Почта", required=True, maxlength=50),
        PasswordField("password", label="Пароль", required=False),
        StringField("firstname", label="Имя", maxlength=50),
        StringField("lastname", label="Фамилия", maxlength=50),
        IntegerField("age", label="Возраст"),
        IntegerField("height", label="Рост (см)"),
        FloatField("weight", label="Вес (кг)"),
        EnumField("gender", label="Пол", choices=GenderEnum.get_admin_choices()),
        EnumField("aim", label="Цель", choices=AimEnum.get_admin_choices()),
        EnumField("activity_level", label="Уровень активности", choices=ActivityLevelEnum.get_admin_choices()),
        FloatField("recommended_calories", label="Рекомендуемые калории"),
        SingleImageField("avatar", label="Аватарка", required=False),
        BooleanField("has_avatar", label="Есть аватар"),
        MoscowDateTimeField("created_at", label="Дата создания", read_only=True),
        MoscowDateTimeField("updated_at", label="Дата обновления", read_only=True),
    ]

    exclude_fields_from_create = ["has_avatar", "created_at", "recommended_calories", "updated_at"]
    exclude_fields_from_edit = ["has_avatar", "created_at", "recommended_calories", "updated_at"]
    exclude_fields_from_list = [
        "hashed_password",
        "password",
        "avatar",
        "activity_level",
        "recommended_calories"
    ]

    def can_create(self, request: Request) -> bool:
        return True

    def can_delete(self, request: Request) -> bool:
        return True

    def can_edit(self, request: Request) -> bool:
        return True

    def _validate_name_field(self, field_name: str, value: str) -> None:
        if value and not value.replace(" ", "").isalpha():
            raise FormValidationError({field_name: "Поле должно содержать только буквы"})
        if value and len(value.split()) != 1:
            raise FormValidationError({field_name: "Поле должно содержать только одно слово"})

    def _validate_numeric_field(self, field_name: str, value, field_type: str) -> None:
        if value is not None:
            try:
                if field_type == "integer":
                    num_value = int(value)
                    if num_value < 0:
                        raise FormValidationError({field_name: "Значение должно быть неотрицательным"})
                    if field_name == "age" and num_value > 150:
                        raise FormValidationError({field_name: "Возраст должен быть реалистичным"})
                    if field_name == "height" and (num_value < 20 or num_value > 300):
                        raise FormValidationError({field_name: "Рост должен быть в диапазоне 20-300 см"})
                elif field_type == "float":
                    num_value = float(value)
                    if num_value < 0:
                        raise FormValidationError({field_name: "Значение должно быть неотрицательным"})
                    if field_name == "weight" and (num_value < 0 or num_value > 500):
                        raise FormValidationError({field_name: "Вес должен быть в диапазоне 0-500 кг"})
            except (ValueError, TypeError):
                raise FormValidationError({field_name: "Некорректное числовое значение"})

    async def before_create(self, request: Request, data: dict, obj: User) -> None:
        errors = {}

        if not data.get("password"):
            errors["password"] = "Пароль обязателен"

        firstname = data.get("firstname")
        if firstname:
            try:
                self._validate_name_field("firstname", firstname)
            except FormValidationError as e:
                errors.update(e.errors)

        lastname = data.get("lastname")
        if lastname:
            try:
                self._validate_name_field("lastname", lastname)
            except FormValidationError as e:
                errors.update(e.errors)

        age = data.get("age")
        if age is not None:
            try:
                self._validate_numeric_field("age", age, "integer")
            except FormValidationError as e:
                errors.update(e.errors)

        height = data.get("height")
        if height is not None:
            try:
                self._validate_numeric_field("height", height, "integer")
            except FormValidationError as e:
                errors.update(e.errors)

        weight = data.get("weight")
        if weight is not None:
            try:
                self._validate_numeric_field("weight", weight, "float")
            except FormValidationError as e:
                errors.update(e.errors)

        recommended_calories = data.get("recommended_calories")
        if recommended_calories is not None:
            try:
                self._validate_numeric_field("recommended_calories", recommended_calories, "float")
            except FormValidationError as e:
                errors.update(e.errors)

        if errors:
            raise FormValidationError(errors)

        obj.hashed_password = Security.get_password_hash(data["password"])
        obj.email = data["login"]

        if data.get("gender"):
            obj.gender = GenderEnum(data["gender"])
        if data.get("aim"):
            obj.aim = AimEnum(data["aim"])
        if data.get("activity_level"):
            obj.activity_level = ActivityLevelEnum(data["activity_level"])

        avatar_file = data.get("avatar")
        if avatar_file and avatar_file[0]:
            try:
                obj.avatar = await self._object_repository.add(avatar_file[0])
            except Exception as e:
                raise FormValidationError({"avatar": "Ошибка загрузки аватара"})
        else:
            obj.avatar = None

    async def before_edit(self, request: Request, data: dict, obj: User) -> None:
        errors = {}

        firstname = data.get("firstname")
        if firstname:
            try:
                self._validate_name_field("firstname", firstname)
            except FormValidationError as e:
                errors.update(e.errors)

        lastname = data.get("lastname")
        if lastname:
            try:
                self._validate_name_field("lastname", lastname)
            except FormValidationError as e:
                errors.update(e.errors)

        age = data.get("age")
        if age is not None:
            try:
                self._validate_numeric_field("age", age, "integer")
            except FormValidationError as e:
                errors.update(e.errors)

        height = data.get("height")
        if height is not None:
            try:
                self._validate_numeric_field("height", height, "integer")
            except FormValidationError as e:
                errors.update(e.errors)

        weight = data.get("weight")
        if weight is not None:
            try:
                self._validate_numeric_field("weight", weight, "float")
            except FormValidationError as e:
                errors.update(e.errors)

        recommended_calories = data.get("recommended_calories")
        if recommended_calories is not None:
            try:
                self._validate_numeric_field("recommended_calories", recommended_calories, "float")
            except FormValidationError as e:
                errors.update(e.errors)

        if errors:
            raise FormValidationError(errors)

        if "password" in data and data["password"]:
            obj.hashed_password = Security.get_password_hash(data["password"])

        if "login" in data:
            obj.email = data["login"]

        if "gender" in data and data["gender"]:
            obj.gender = GenderEnum(data["gender"])
        if "aim" in data and data["aim"]:
            obj.aim = AimEnum(data["aim"])
        if "activity_level" in data and data["activity_level"]:
            obj.activity_level = ActivityLevelEnum(data["activity_level"])

        form_data = await request.form()
        delete_avatar = form_data.get("_avatar-delete") == "on"

        current_avatar = obj.avatar

        if delete_avatar and current_avatar:
            try:
                await self._object_repository.delete(current_avatar)
                obj.avatar = None
            except Exception as e:
                raise FormValidationError({"avatar": "Ошибка удаления аватара"})

        avatar_file = data.get("avatar")
        if avatar_file and avatar_file[0]:
            try:
                if current_avatar and not delete_avatar:
                    await self._object_repository.delete(current_avatar)

                obj.avatar = await self._object_repository.add(avatar_file[0])
            except Exception as e:
                raise FormValidationError({"avatar": "Ошибка обновления аватара"})

    async def after_delete(self, request: Request, obj: User) -> None:
        try:
            if obj.avatar:
                await self._object_repository.delete(obj.avatar)
        except Exception as e:
            raise FormValidationError({"avatar": "Ошибка удаления аватара"})


class ProductView(ModelView, MixinImageControl):
    def __init__(
        self,
        object_repository: BaseObjectRepository,
    ):
        self._object_repository = object_repository
        super().__init__(
            model=Product,
            name="продукт",
            icon="fa-solid fa-boxes-stacked",
            label="Продукты"
        )

    permission_view = PermissionsEnum.PRODUCTS_VIEW
    permission_create = PermissionsEnum.PRODUCTS_CREATE
    permission_edit = PermissionsEnum.PRODUCTS_EDIT
    permission_delete = PermissionsEnum.PRODUCTS_DELETE

    list_template = "clickable_raw.html"

    fields = [
        "id",
        StringField("name", label="Название", required=True, maxlength=100),
        SlugTargetField(
            "slug",
            label="Slug",
            required=False,
            maxlength=1200,
            placeholder="Оставить поле пустым для автоматической генерации",
            form_template="forms/slug_field.html",
            model=Product,
        ),
        FloatField("weight", label="Вес (г)", required=True),
        FloatField("calories", label="Калории (ккал)", required=True),
        FloatField("proteins", label="Белки (г)", required=True),
        FloatField("fats", label="Жиры (г)", required=True),
        FloatField("carbohydrates", label="Углеводы (г)", required=True),
        TextAreaField("description", label="Описание"),
        ProductCoverField("cover", label="Обложка", required=False, form_template="forms/product_cover_field.html"),
        ProductsFiles(
            "extra_media", label="Другие фото", required=False, multiple=True, form_template="forms/multiple_files.html"
        ),
        HasOne("user", label="Создатель", identity="user", read_only=True),
        HasOne("brand", label="Бренд", identity="brand"),
        MoscowDateTimeField("created_at", label="Дата создания", read_only=True),
        MoscowDateTimeField("updated_at", label="Дата обновления", read_only=True),
        BooleanField("is_public", label="Публичный"),
        BooleanField("is_active", label="Активен",),
    ]

    exclude_fields_from_create = ["created_at", "user", "updated_at"]
    exclude_fields_from_edit = ["created_at", "user", "updated_at"]
    exclude_fields_from_list = ["extra_media", "description"]

    async def _check_name_exists(self, name: str, exclude_id: str = None) -> bool:
        async with async_session_maker() as session:
            stmt = select(Product).where(Product.name == name)
            if exclude_id:
                stmt = stmt.where(Product.id != exclude_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def _check_slug_exists(self, slug: str, exclude_id: str = None) -> bool:
        async with async_session_maker() as session:
            stmt = select(Product).where(Product.slug == slug)
            if exclude_id:
                stmt = stmt.where(Product.id != exclude_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def before_create(self, request: Request, data: dict, obj: Product) -> None:
        errors = {}
        if data["cover"][0] is None:
            errors["cover"] = "Поле не должно быть пустым"

        if data["extra_media"][0] == []:
            errors["extra_media"] = "Поле не должно быть пустым"

        if errors:
            raise FormValidationError(errors)

        name = data.get("name")
        if not name:
            raise FormValidationError({"name": "Название обязательно для заполнения"})

        if await self._check_name_exists(name):
            raise FormValidationError({"name": "Продукт с таким названием уже существует"})

        slug = data.get("slug")
        if not slug:
            async with async_session_maker() as session:
                slug = await generate_unique_slug(session, name, Product)
        else:
            if await self._check_slug_exists(slug):
                raise FormValidationError({"slug": "Продукт с таким slug уже существует"})

        obj.slug = slug

        try:
            weight = float(data.get("weight", 0))
            calories = float(data.get("calories", 0))
            proteins = float(data.get("proteins", 0))
            fats = float(data.get("fats", 0))
            carbohydrates = float(data.get("carbohydrates", 0))

            if weight <= 0:
                raise FormValidationError({"weight": "Вес должен быть положительным числом"})
            if calories < 0:
                raise FormValidationError({"calories": "Калории не могут быть отрицательными"})
            if proteins < 0:
                raise FormValidationError({"proteins": "Белки не могут быть отрицательными"})
            if fats < 0:
                raise FormValidationError({"fats": "Жиры не могут быть отрицательными"})
            if carbohydrates < 0:
                raise FormValidationError({"carbohydrates": "Углеводы не могут быть отрицательными"})

        except (ValueError, TypeError):
            raise FormValidationError({"weight": "Все числовые поля должны быть валидными числами"})

        images = {
            "cover": await self._object_repository.add(data["cover"][0]),
            "extra_media": [await self._object_repository.add(f) for f in data["extra_media"][0]],
        }

        obj.images = images

    async def before_edit(
            self,
            request: Request,
            data: dict,
            obj: Product,
    ) -> None:
        errors = {}
        if data["cover"][0] is None and not getattr(obj, 'images', {}).get("cover"):
            errors["cover"] = "Поле не должно быть пустым"

        if errors:
            raise FormValidationError(errors)

        name = data.get("name")
        if name and name != obj.name:
            if await self._check_name_exists(name, str(obj.id)):
                raise FormValidationError({"name": "Продукт с таким названием уже существует"})

        slug = data.get("slug")
        if slug and slug != obj.slug:
            if await self._check_slug_exists(slug, str(obj.id)):
                raise FormValidationError({"slug": "Продукт с таким slug уже существует"})

        try:
            weight = data.get("weight")
            if weight is not None:
                weight_val = float(weight)
                if weight_val <= 0:
                    raise FormValidationError({"weight": "Вес должен быть положительным числом"})

            calories = data.get("calories")
            if calories is not None:
                calories_val = float(calories)
                if calories_val < 0:
                    raise FormValidationError({"calories": "Калории не могут быть отрицательными"})

            proteins = data.get("proteins")
            if proteins is not None:
                proteins_val = float(proteins)
                if proteins_val < 0:
                    raise FormValidationError({"proteins": "Белки не могут быть отрицательными"})

            fats = data.get("fats")
            if fats is not None:
                fats_val = float(fats)
                if fats_val < 0:
                    raise FormValidationError({"fats": "Жиры не могут быть отрицательными"})

            carbohydrates = data.get("carbohydrates")
            if carbohydrates is not None:
                carbohydrates_val = float(carbohydrates)
                if carbohydrates_val < 0:
                    raise FormValidationError({"carbohydrates": "Углеводы не могут быть отрицательными"})

        except (ValueError, TypeError):
            raise FormValidationError({"weight": "Все числовые поля должны быть валидными числами"})

        await self._handle_image_updates(request, data, obj)

    async def _handle_image_updates(self, request: Request, data: dict, obj: Product) -> None:
        form_data = await request.form()
        files_to_delete = form_data.getlist("_extra_media-delete")
        delete_cover = form_data.get("_cover-delete") == "on"

        current_images = getattr(obj, 'images', {}) or {}
        current_cover = current_images.get('cover')
        current_extra_media = current_images.get('extra_media', [])

        updated_images = current_images.copy()

        if delete_cover and current_cover:
            try:
                await self._object_repository.delete(current_cover)
                updated_images["cover"] = None
                current_cover = None
            except Exception as e:
                print(f"Ошибка при удалении обложки: {e}")

        new_cover_file = data["cover"][0]
        if new_cover_file is not None:
            if current_cover:
                try:
                    await self._object_repository.delete(current_cover)
                except Exception as e:
                    print(f"Ошибка при удалении старой обложки: {e}")

            updated_images["cover"] = await self._object_repository.add(new_cover_file)

        if files_to_delete:
            current_extra_media = [f for f in current_extra_media if f not in files_to_delete]

            for filename in files_to_delete:
                try:
                    await self._object_repository.delete(filename)
                except Exception as e:
                    print(f"Ошибка при удалении файла {filename}: {e}")

        new_extra_media_files = data["extra_media"][0] or []
        new_filenames = []

        if new_extra_media_files and new_extra_media_files != []:
            for file in new_extra_media_files:
                if hasattr(file, 'filename') and file.filename:
                    filename = await self._object_repository.add(file)
                    new_filenames.append(filename)

        updated_images["extra_media"] = current_extra_media + new_filenames

        obj.images = updated_images

    async def before_delete(self, request: Request, obj: Product) -> None:
        images = getattr(obj, 'images', {}) or {}

        cover = images.get('cover')
        if cover:
            try:
                await self._object_repository.delete(cover)
            except Exception as e:
                print(f"Ошибка при удалении обложки: {e}")

        extra_media = images.get('extra_media', [])
        for filename in extra_media:
            try:
                await self._object_repository.delete(filename)
            except Exception as e:
                print(f"Ошибка при удалении медиафайла {filename}: {e}")


class BrandView(ModelView):
    def __init__(self):
        super().__init__(
            model=Brand,
            name="бренд",
            icon="fa-solid fa-tag",
            label="Бренды"
        )

    list_template = "clickable_raw.html"

    fields = [
        "id",
        StringField("title", label="Название", required=True, maxlength=100),
        HasMany("products", label="Продукты", identity="product"),
        MoscowDateTimeField("created_at", label="Дата создания", read_only=True),
        MoscowDateTimeField("updated_at", label="Дата обновления", read_only=True),
    ]

    exclude_fields_from_create = ["created_at", "updated_at"]
    exclude_fields_from_edit = ["created_at", "updated_at"]
    exclude_fields_from_list = ["products"]

    async def _check_title_exists(self, title: str, exclude_id: str = None) -> bool:
        async with async_session_maker() as session:
            stmt = select(Brand).where(Brand.title == title)
            if exclude_id:
                stmt = stmt.where(Brand.id != exclude_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def before_create(self, request: Request, data: dict, obj: Brand) -> None:
        title = data.get("title")
        if not title:
            raise FormValidationError({"title": "Название обязательно для заполнения"})

        if await self._check_title_exists(title):
            raise FormValidationError({"title": "Бренд с таким названием уже существует"})

        obj.title = title

    async def before_edit(
            self,
            request: Request,
            data: dict,
            obj: Brand,
    ) -> None:
        title = data.get("title")
        if title and title != obj.title:
            if await self._check_title_exists(title, str(obj.id)):
                raise FormValidationError({"title": "Бренд с таким названием уже существует"})

    async def before_delete(self, request: Request, obj: Brand) -> None:
        async with async_session_maker() as session:
            stmt = select(Product).where(Product.brand_id == obj.id)
            result = await session.execute(stmt)
            products = result.scalars().all()

            if products:
                product_names = [product.name for product in products[:5]]
                raise FormValidationError({
                    "brand": f"Невозможно удалить бренд, так как с ним связаны продукты: {', '.join(product_names)}"
                    f"{' и другие...' if len(products) > 5 else ''}"
                })
