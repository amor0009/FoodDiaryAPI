from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.core.security import Security
from api.src.database.database import get_async_session
from api.src.dependencies.repositories import get_user_repository
from api.src.models.user import User
from api.src.schemas.family import (
    FamilyRead, FamilyCreate, FamilyMemberRead, FamilyProductRead,
    FamilyProductCreate, FamilyInvitationRead, FamilyInvitationCreate,
    FamilyNotificationRead, FamilyMemberRoleUpdate, FamilyUpdate
)
from api.src.dependencies.services import (
    get_family_service, get_family_member_service,
    get_family_product_service, get_family_invitation_service,
    get_family_notification_service
)


family_router = APIRouter(prefix="/api/families", tags=["families"])


@family_router.post("/")
async def create_family(
        family_data: FamilyCreate,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_service=Depends(get_family_service),
) -> FamilyRead:
    return await family_service.create_family(session, family_data, current_user.id)


@family_router.get("/")
async def get_user_families(
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_service=Depends(get_family_service),
) -> list[FamilyRead]:
    return await family_service.get_user_families(session, current_user.id)


@family_router.get("/{family_id}")
async def get_family(
        family_id: UUID,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_service=Depends(get_family_service),
) -> FamilyRead:
    return await family_service.get_family_by_id(session, family_id, current_user.id)


@family_router.patch("/{family_id}")
async def update_family(
        family_id: UUID,
        family_update: FamilyUpdate,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_service=Depends(get_family_service),
) -> FamilyRead:
    return await family_service.update_family(session, family_id, family_update, current_user.id)


@family_router.delete("/{family_id}")
async def delete_family(
        family_id: UUID,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_service=Depends(get_family_service),
) -> dict:
    return await family_service.delete_family(session, family_id, current_user.id)


@family_router.get("/{family_id}/members")
async def get_family_members(
        family_id: UUID,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_member_service=Depends(get_family_member_service),
) -> list[FamilyMemberRead]:
    return await family_member_service.get_family_members(session, family_id, current_user.id)


@family_router.patch("/{family_id}/members/{user_id}/role")
async def update_member_role(
        family_id: UUID,
        user_id: UUID,
        role_update: FamilyMemberRoleUpdate,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_member_service=Depends(get_family_member_service),
        notification_service=Depends(get_family_notification_service),
        user_repository=Depends(get_user_repository)
) -> FamilyMemberRead:
    updated_member = await family_member_service.update_member_role(
        session, family_id, user_id, current_user.id, role_update.role
    )

    if updated_member.user_id != current_user.id:
        current_user_data = await user_repository.get_user_by_id(session, current_user.id)
        await notification_service.create_role_changed_notification(
            session=session,
            user_id=user_id,
            family_id=family_id,
            new_role=role_update.role.value,
            changed_by_email=current_user_data.email if current_user_data else current_user.email
        )

    return updated_member


@family_router.delete("/{family_id}/members/{user_id}")
async def remove_member(
        family_id: UUID,
        user_id: UUID,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_member_service=Depends(get_family_member_service),
) -> dict:
    return await family_member_service.remove_member(session, family_id, user_id, current_user.id)


@family_router.post("/{family_id}/invitations")
async def create_invitation(
        family_id: UUID,
        invitation_data: FamilyInvitationCreate,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_invitation_service=Depends(get_family_invitation_service),
) -> FamilyInvitationRead:
    return await family_invitation_service.create_invitation(
        session, family_id, invitation_data, current_user.id
    )


@family_router.get("/{family_id}/invitations")
async def get_family_invitations(
        family_id: UUID,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_invitation_service=Depends(get_family_invitation_service),
) -> list[FamilyInvitationRead]:
    return await family_invitation_service.get_family_invitations(session, family_id, current_user.id)


@family_router.get("/invitations/my")
async def get_my_invitations(
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_invitation_service=Depends(get_family_invitation_service),
) -> list[FamilyInvitationRead]:
    return await family_invitation_service.get_user_invitations(session, current_user.email)


@family_router.post("/invitations/{token}/accept")
async def accept_invitation(
        token: str,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_invitation_service=Depends(get_family_invitation_service),
) -> dict:
    return await family_invitation_service.accept_invitation(session, token, current_user.email)


@family_router.post("/invitations/{token}/decline")
async def decline_invitation(
        token: str,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_invitation_service=Depends(get_family_invitation_service),
) -> dict:
    return await family_invitation_service.decline_invitation(session, token, current_user.email)


@family_router.delete("/invitations/{invitation_id}")
async def cancel_invitation(
        invitation_id: UUID,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_invitation_service=Depends(get_family_invitation_service),
) -> dict:
    return await family_invitation_service.cancel_invitation(session, invitation_id, current_user.id)


@family_router.post("/{family_id}/products")
async def add_product_to_family(
        family_id: UUID,
        product_data: FamilyProductCreate,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_product_service=Depends(get_family_product_service),
) -> FamilyProductRead:
    return await family_product_service.add_product_to_family(
        session, family_id, product_data, current_user.id
    )


@family_router.get("/{family_id}/products")
async def get_family_products(
        family_id: UUID,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_product_service=Depends(get_family_product_service),
) -> list[FamilyProductRead]:
    return await family_product_service.get_family_products(session, family_id, current_user.id)


@family_router.delete("/{family_id}/products/{product_id}")
async def remove_product_from_family(
        family_id: UUID,
        product_id: UUID,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        family_product_service=Depends(get_family_product_service),
) -> dict:
    return await family_product_service.remove_product_from_family(session, family_id, product_id, current_user.id)


@family_router.get("/notifications")
async def get_family_notifications(
        is_read: bool | None = Query(None, description="Фильтр по статусу прочтения"),
        limit: int = Query(50, ge=1, le=100, description="Лимит уведомлений"),
        offset: int = Query(0, ge=0, description="Смещение"),
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        notification_service=Depends(get_family_notification_service),
) -> list[FamilyNotificationRead]:
    return await notification_service.get_user_notifications(
        session=session,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        is_read=is_read
    )


@family_router.get("/notifications/unread-count")
async def get_unread_notifications_count(
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        notification_service=Depends(get_family_notification_service),
) -> dict:
    return await notification_service.get_unread_count(session, current_user.id)


@family_router.patch("/notifications/{notification_id}/read")
async def mark_notification_as_read(
        notification_id: UUID,
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        notification_service=Depends(get_family_notification_service),
) -> FamilyNotificationRead:
    return await notification_service.mark_notification_as_read(
        session=session,
        notification_id=notification_id,
        user_id=current_user.id
    )


@family_router.post("/notifications/mark-all-read")
async def mark_all_notifications_as_read(
        current_user: User = Depends(Security.get_required_user),
        session: AsyncSession = Depends(get_async_session),
        notification_service=Depends(get_family_notification_service),
) -> dict:
    return await notification_service.mark_all_notifications_as_read(session, current_user.id)
