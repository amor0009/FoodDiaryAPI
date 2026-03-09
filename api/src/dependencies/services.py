from api.src.dependencies.repositories import get_user_repository, get_meal_repository, get_meal_products_repository, \
    get_user_weight_repository, get_product_repository, get_object_repository, get_family_repository, \
    get_family_member_repository, get_family_product_repository, get_family_invitation_repository, \
    get_family_notification_repository
from api.src.services.family import FamilyService, FamilyMemberService, FamilyProductService, FamilyInvitationService, \
    FamilyNotificationService
from api.src.services.meal import MealService
from api.src.services.product import ProductService
from api.src.services.user import UserService
from api.src.services.user_weight import UserWeightService


def get_user_service() -> UserService:
    return UserService(get_user_repository(), get_user_weight_repository(), get_user_weight_service(), get_object_repository())


def get_meal_service() -> MealService:
    return MealService(get_meal_repository(), get_meal_products_repository())


def get_product_service() -> ProductService:
    return ProductService(get_product_repository(), get_object_repository())


def get_user_weight_service() -> UserWeightService:
    return UserWeightService(get_user_weight_repository(), get_user_repository())


def get_family_service() -> FamilyService:
    return FamilyService(
        get_family_repository(),
        get_family_member_repository()
    )


def get_family_member_service() -> FamilyMemberService:
    return FamilyMemberService(
        get_family_member_repository()
    )


def get_family_product_service() -> FamilyProductService:
    return FamilyProductService(
        get_family_product_repository(),
        get_family_member_repository()
    )


def get_family_invitation_service() -> FamilyInvitationService:
    return FamilyInvitationService(
        get_family_invitation_repository(),
        get_family_member_repository(),
        get_user_repository(),
        get_family_notification_service()
    )


def get_family_notification_service() -> FamilyNotificationService:
    return FamilyNotificationService(
        get_family_notification_repository(),
        get_family_member_repository(),
        get_user_repository(),
        get_family_repository()
    )
