from api.src.admin.auth import AdminAuth, admin_auth
from api.src.admin.views import StaffView, ProductView, UserView, RoleView, PermissionView, BrandView
from api.src.database.database import engine
from starlette_admin.contrib.sqla import Admin
from starlette_admin.i18n import I18nConfig
from starlette_admin import DropDown

from api.src.dependencies.repositories import get_object_repository

admin = Admin(
    engine=engine,
    title="FoodDiary",
    auth_provider=admin_auth,
    templates_dir="api/src/templates",
    i18n_config=I18nConfig(default_locale="ru"),
)

admin.add_view(
    DropDown(
        label="Персонал и роли",
        icon="fa-solid fa-user-tie",
        views=[
            StaffView,
            RoleView,
            PermissionView,
        ],
    )
)

admin.add_view(UserView(object_repository=get_object_repository()))

admin.add_view(
    DropDown(
        label="Продукты и бренды",
        icon="fa-solid fa-boxes-stacked",
        views=[
            ProductView(object_repository=get_object_repository()),
            BrandView,
        ],
    )
)
