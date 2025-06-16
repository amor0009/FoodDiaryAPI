from src.admin.auth import AdminAuth
from src.admin.views import StaffView, ProductView, UserView
from src.database.database import engine
from starlette_admin.contrib.sqla import Admin
from starlette_admin.i18n import I18nConfig

admin = Admin(
    engine=engine,
    title="FoodDiary",
    auth_provider=AdminAuth(),
    templates_dir="src/templates",
    i18n_config=I18nConfig(default_locale="ru"),
)

admin.add_view(StaffView)
admin.add_view(UserView)
admin.add_view(ProductView)
