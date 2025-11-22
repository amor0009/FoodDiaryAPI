from api.src.repositories.meal.base import BaseMealRepository
from api.src.repositories.meal.sqlalchemy import SqlAlchemyMealRepository
from api.src.repositories.meal_products.base import BaseMealProductsRepository
from api.src.repositories.meal_products.sqlalchemy import SqlAlchemyMealProductsRepository
from api.src.repositories.objects.base import BaseObjectRepository
from api.src.repositories.objects.s3 import S3ObjectRepository
from api.src.repositories.product.base import BaseProductRepository
from api.src.repositories.product.sqlalchemy import SqlAlchemyProductRepository
from api.src.repositories.staff.base import BaseStaffRepository
from api.src.repositories.staff.sqlalchemy import SqlAlchemyStaffRepository
from api.src.repositories.user.base import BaseUserRepository
from api.src.repositories.user.sqlalchemy import SqlAlchemyUserRepository
from api.src.repositories.user_weight.base import BaseUserWeightRepository
from api.src.repositories.user_weight.sqlalchemy import SqlAlchemyUserWeightRepository


def get_user_repository() -> BaseUserRepository:
    return SqlAlchemyUserRepository()


def get_meal_repository() -> BaseMealRepository:
    return SqlAlchemyMealRepository()


def get_meal_products_repository() -> BaseMealProductsRepository:
    return SqlAlchemyMealProductsRepository()


def get_object_repository() -> BaseObjectRepository:
    return S3ObjectRepository()


def get_product_repository() -> BaseProductRepository:
    return SqlAlchemyProductRepository()


def get_staff_repository() -> BaseStaffRepository:
    return SqlAlchemyStaffRepository()


def get_user_weight_repository() -> BaseUserWeightRepository:
    return SqlAlchemyUserWeightRepository()
