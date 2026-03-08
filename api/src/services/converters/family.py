from uuid import UUID
from api.src.models.family import Family, FamilyMember, FamilyProduct, FamilyInvitation, FamilyNotification
from api.src.schemas.family import (
    FamilyRead, FamilyMemberRead, FamilyProductRead, FamilyInvitationRead, FamilyNotificationRead
)


def convert_family_model_to_schema(family_model: Family, members_count: int = 0, products_count: int = 0) -> FamilyRead:
    return FamilyRead(
        id=family_model.id,
        name=family_model.name,
        description=family_model.description,
        is_active=family_model.is_active,
        created_by=family_model.created_by,
        created_at=family_model.created_at,
        updated_at=family_model.updated_at,
        members_count=members_count,
        products_count=products_count
    )


def convert_family_member_model_to_schema(
        member_model: FamilyMember,
        current_user_id: UUID | None = None,
        family_product: FamilyProduct | None = None
) -> FamilyMemberRead:
    can_edit_family_product = False
    if family_product and current_user_id:
        can_edit_family_product = member_model.can_edit_family_product(family_product)

    return FamilyMemberRead(
        id=member_model.id,
        family_id=member_model.family_id,
        user_id=member_model.user_id,
        role=member_model.role,
        created_at=member_model.created_at,
        updated_at=member_model.updated_at,
        user_email=member_model.user.email,
        user_firstname=member_model.user.firstname,
        user_lastname=member_model.user.lastname,
        can_manage_family_products=member_model.can_manage_family_products,
        can_edit_family_product=can_edit_family_product
    )


def convert_family_product_model_to_schema(
        family_product_model: FamilyProduct,
        current_user_id: UUID | None = None
) -> FamilyProductRead:
    can_edit = False
    can_delete = False

    if current_user_id:
        if callable(family_product_model.can_edit):
            try:
                can_edit = family_product_model.can_edit(current_user_id)
            except TypeError as e:
                can_edit = family_product_model.added_by == current_user_id
        else:
            can_edit = family_product_model.added_by == current_user_id

        can_delete = can_edit

    return FamilyProductRead(
        id=family_product_model.id,
        family_id=family_product_model.family_id,
        product_id=family_product_model.product_id,
        added_by=family_product_model.added_by,
        created_at=family_product_model.created_at,
        updated_at=family_product_model.updated_at,
        product_name=family_product_model.product.name,
        product_weight=family_product_model.product.weight,
        product_calories=family_product_model.product.calories,
        added_by_email=family_product_model.added_by_user.email,
        can_edit=can_edit,
        can_delete=can_delete
    )


def convert_family_invitation_model_to_schema(invitation_model: FamilyInvitation) -> FamilyInvitationRead:
    return FamilyInvitationRead(
        id=invitation_model.id,
        family_id=invitation_model.family_id,
        email=invitation_model.email,
        invited_by=invitation_model.invited_by,
        role=invitation_model.role,
        status=invitation_model.status,
        token=invitation_model.token,
        expires_at=invitation_model.expires_at,
        created_at=invitation_model.created_at,
        updated_at=invitation_model.updated_at,
        family_name=invitation_model.family.name,
        inviter_email=invitation_model.inviter.email
    )


def convert_family_notification_model_to_schema(notification_model: FamilyNotification) -> FamilyNotificationRead:

    family_name = notification_model.family.name if notification_model.family else None

    inviter_email = None
    if notification_model.invitation and notification_model.invitation.inviter:
        inviter_email = notification_model.invitation.inviter.email

    return FamilyNotificationRead(
        id=notification_model.id,
        user_id=notification_model.user_id,
        family_id=notification_model.family_id,
        invitation_id=notification_model.invitation_id,
        type=notification_model.type,
        title=notification_model.title,
        message=notification_model.message,
        is_read=notification_model.is_read,
        read_at=notification_model.read_at,
        created_at=notification_model.created_at,
        updated_at=notification_model.updated_at,
        family_name=family_name,
        inviter_email=inviter_email
    )
