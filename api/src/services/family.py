from dataclasses import dataclass
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from api.logging_config import logger
from api.src.models.family import FamilyRole, InvitationStatus, FamilyNotification, FamilyMember, FamilyInvitation, \
    FamilyProduct
from api.src.repositories.family.base import BaseFamilyRepository, BaseFamilyMemberRepository, \
    BaseFamilyProductRepository, BaseFamilyInvitationRepository, BaseFamilyNotificationRepository
from api.src.repositories.user.base import BaseUserRepository
from api.src.schemas.family import (
    FamilyRead, FamilyCreate, FamilyMemberRead, FamilyProductRead,
    FamilyProductCreate, FamilyInvitationRead, FamilyInvitationCreate,
    FamilyUpdate, FamilyNotificationRead, FamilyMemberRoleUpdate
)
from api.src.services.converters.family import (
    convert_family_model_to_schema, convert_family_member_model_to_schema,
    convert_family_product_model_to_schema, convert_family_invitation_model_to_schema,
    convert_family_notification_model_to_schema
)


@dataclass(slots=True)
class FamilyService:
    _family_repository: BaseFamilyRepository
    _family_member_repository: BaseFamilyMemberRepository

    async def create_family(self, session: AsyncSession, family_data: FamilyCreate, user_id: UUID) -> FamilyRead:
        logger.info(f"Creating family for user {user_id}: {family_data.name}")

        try:
            family_dict = family_data.model_dump()
            family_dict["created_by"] = user_id

            family = await self._family_repository.create_family(session, family_dict)
            await session.flush()

            member = await self._family_member_repository.add_member(session, {
                "family_id": family.id,
                "user_id": user_id,
                "role": FamilyRole.OWNER
            })

            await session.commit()
            await session.refresh(family)

            logger.info(f"Family {family_data.name} created successfully by user {user_id}")
            return convert_family_model_to_schema(family)

        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating family {family_data.name}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create family"
            )

    async def get_user_families(self, session: AsyncSession, user_id: UUID) -> list[FamilyRead]:
        logger.info(f"Getting families for user {user_id}")

        families = await self._family_repository.get_user_families(session, user_id)

        family_schemas = []
        for family in families:
            members = await self._family_member_repository.get_family_members(session, family.id)
            products_count = len(family.shared_products) if hasattr(family, 'shared_products') else 0

            family_schemas.append(convert_family_model_to_schema(
                family,
                members_count=len(members),
                products_count=products_count
            ))

        return family_schemas

    async def get_family_by_id(self, session: AsyncSession, family_id: UUID, user_id: UUID) -> FamilyRead:
        logger.info(f"Getting family {family_id} for user {user_id}")

        member = await self._family_member_repository.get_family_member(session, family_id, user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this family"
            )

        family = await self._family_repository.get_family_by_id(session, family_id)
        if not family:
            raise HTTPException(status_code=404, detail="Family not found")

        members = await self._family_member_repository.get_family_members(session, family_id)

        return convert_family_model_to_schema(
            family,
            members_count=len(members),
            products_count=len(family.shared_products)
        )

    async def update_family(self, session: AsyncSession, family_id: UUID, family_update: FamilyUpdate,
                            user_id: UUID) -> FamilyRead:
        logger.info(f"Updating family {family_id} by user {user_id}")

        member = await self._family_member_repository.get_family_member(session, family_id, user_id)
        if not member or not member.can_manage_family_products:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to update family"
            )

        family = await self._family_repository.get_family_by_id(session, family_id)
        if not family:
            raise HTTPException(status_code=404, detail="Family not found")

        try:
            update_data = family_update.model_dump(exclude_unset=True)
            updated_family = await self._family_repository.update_family(session, family, update_data)

            await session.commit()
            logger.info(f"Family {family_id} updated successfully")

            members = await self._family_member_repository.get_family_members(session, family_id)
            return convert_family_model_to_schema(
                updated_family,
                members_count=len(members),
                products_count=len(updated_family.shared_products)
            )

        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating family {family_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update family"
            )

    async def delete_family(self, session: AsyncSession, family_id: UUID, user_id: UUID) -> dict:
        logger.info(f"Deleting family {family_id} by user {user_id}")

        member = await self._family_member_repository.get_family_member(session, family_id, user_id)
        if not member or member.role != FamilyRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only family owner can delete family"
            )

        family = await self._family_repository.get_family_by_id(session, family_id)
        if not family:
            raise HTTPException(status_code=404, detail="Family not found")

        try:
            await self._family_repository.delete_family(session, family)
            await session.commit()
            logger.info(f"Family {family_id} deleted successfully")
            return {"message": "Family deleted successfully"}

        except Exception as e:
            await session.rollback()
            logger.error(f"Error deleting family {family_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete family"
            )


@dataclass(slots=True)
class FamilyMemberService:
    _family_member_repository: BaseFamilyMemberRepository

    async def get_family_members(self, session: AsyncSession, family_id: UUID, user_id: UUID) -> list[FamilyMemberRead]:
        logger.info(f"Getting members for family {family_id} by user {user_id}")

        current_user_member = await self._family_member_repository.get_family_member(session, family_id, user_id)
        if not current_user_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this family"
            )

        members = await self._family_member_repository.get_family_members(session, family_id)

        return [
            convert_family_member_model_to_schema(member, user_id)
            for member in members
        ]

    async def update_member_role(
            self,
            session: AsyncSession,
            family_id: UUID,
            target_user_id: UUID,
            current_user_id: UUID,
            new_role: FamilyRole
    ) -> FamilyMemberRead:
        logger.info(f"Updating role for user {target_user_id} in family {family_id}")

        current_user_member = await self._family_member_repository.get_family_member(
            session, family_id, current_user_id
        )
        if not current_user_member or not current_user_member.can_manage_family_products:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to manage members"
            )

        target_member = await self._family_member_repository.get_family_member(session, family_id, target_user_id)
        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )

        try:
            updated_member = await self._family_member_repository.update_member_role(
                session, target_member, new_role
            )

            await session.commit()

            stmt = select(FamilyMember).where(FamilyMember.id == updated_member.id).options(
                selectinload(FamilyMember.user),
                selectinload(FamilyMember.family)
            )
            result = await session.execute(stmt)
            reloaded_member = result.scalar_one()

            logger.info(f"Role updated for user {target_user_id} in family {family_id}")
            return convert_family_member_model_to_schema(reloaded_member, current_user_id)

        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating member role: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update member role"
            )

    async def remove_member(self, session: AsyncSession, family_id: UUID, target_user_id: UUID,
                            current_user_id: UUID) -> dict:
        logger.info(f"Removing member {target_user_id} from family {family_id}")

        current_user_member = await self._family_member_repository.get_family_member(session, family_id,
                                                                                     current_user_id)
        if not current_user_member or not current_user_member.can_manage_family_products:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to remove members"
            )

        if target_user_id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove yourself from family"
            )

        target_member = await self._family_member_repository.get_family_member(session, family_id, target_user_id)
        if not target_member:
            raise HTTPException(status_code=404, detail="Member not found")

        try:
            await self._family_member_repository.remove_member(session, target_member)
            await session.commit()
            logger.info(f"Member {target_user_id} removed from family {family_id}")
            return {"message": "Member removed successfully"}

        except Exception as e:
            await session.rollback()
            logger.error(f"Error removing member: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove member"
            )


@dataclass(slots=True)
class FamilyProductService:
    _family_product_repository: BaseFamilyProductRepository
    _family_member_repository: BaseFamilyMemberRepository

    async def add_product_to_family(
            self,
            session: AsyncSession,
            family_id: UUID,
            product_data: FamilyProductCreate,
            user_id: UUID
    ) -> FamilyProductRead:
        logger.info(f"Adding product {product_data.product_id} to family {family_id} by user {user_id}")

        member = await self._family_member_repository.get_family_member(session, family_id, user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this family"
            )

        existing = await self._family_product_repository.get_family_product(session, family_id, product_data.product_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product already exists in this family"
            )

        try:
            family_product = await self._add_product_with_relations(
                session, family_id, product_data.product_id, user_id
            )

            await session.commit()
            logger.info(f"Product {product_data.product_id} added to family {family_id}")

            return convert_family_product_model_to_schema(family_product, user_id)

        except Exception as e:
            await session.rollback()
            logger.error(f"Error adding product to family: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add product to family"
            )

    async def _add_product_with_relations(
            self,
            session: AsyncSession,
            family_id: UUID,
            product_id: UUID,
            user_id: UUID
    ) -> FamilyProduct:
        family_product = FamilyProduct(
            family_id=family_id,
            product_id=product_id,
            added_by=user_id
        )

        session.add(family_product)
        await session.flush()

        stmt = (
            select(FamilyProduct)
            .where(FamilyProduct.id == family_product.id)
            .options(
                selectinload(FamilyProduct.family),
                selectinload(FamilyProduct.product),
                selectinload(FamilyProduct.added_by_user)
            )
        )

        result = await session.execute(stmt)
        return result.scalar_one()

    async def get_family_products(
            self,
            session: AsyncSession,
            family_id: UUID,
            user_id: UUID
    ) -> list[FamilyProductRead]:
        logger.info(f"Getting products for family {family_id} by user {user_id}")

        member = await self._family_member_repository.get_family_member(session, family_id, user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this family"
            )

        family_products = await self._family_product_repository.get_family_products(session, family_id)

        return [
            convert_family_product_model_to_schema(fp, user_id)
            for fp in family_products
        ]

    async def remove_product_from_family(
            self,
            session: AsyncSession,
            family_id: UUID,
            product_id: UUID,
            user_id: UUID
    ) -> dict:
        logger.info(f"Removing product {product_id} from family {family_id} by user {user_id}")

        member = await self._family_member_repository.get_family_member(session, family_id, user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this family"
            )

        family_product = await self._family_product_repository.get_family_product(session, family_id, product_id)
        if not family_product:
            raise HTTPException(status_code=404, detail="Product not found in family")

        if not member.can_edit_family_product(family_product):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to remove this product"
            )

        try:
            await self._family_product_repository.remove_product_from_family(session, family_product)
            await session.commit()
            logger.info(f"Product {product_id} removed from family {family_id}")
            return {"message": "Product removed from family successfully"}

        except Exception as e:
            await session.rollback()
            logger.error(f"Error removing product from family: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove product from family"
            )


@dataclass(slots=True)
class FamilyNotificationService:
    _notification_repository: BaseFamilyNotificationRepository
    _family_member_repository: BaseFamilyMemberRepository
    _user_repository: BaseUserRepository
    _family_repository: BaseFamilyRepository

    async def create_invitation_notification(
            self,
            session: AsyncSession,
            user_id: UUID,
            family_id: UUID,
            invitation_id: UUID | None = None,
            inviter_email: str | None = None,
            family_name: str | None = None
    ) -> FamilyNotification:
        if not family_name:
            family = await self._family_repository.get_family_by_id(session, family_id)
            family_name = family.name if family else "Семья"

        notification_data = {
            "user_id": user_id,
            "family_id": family_id,
            "invitation_id": invitation_id,
            "type": "invitation",
            "title": "Приглашение в семью",
            "message": f"Пользователь {inviter_email or 'неизвестный'} пригласил вас в семью '{family_name}'",
            "is_read": False
        }

        return await self._notification_repository.create_notification(session, notification_data)

    async def create_product_added_notification(
            self,
            session: AsyncSession,
            family_id: UUID,
            product_name: str,
            added_by_email: str,
            exclude_user_id: UUID | None = None
    ) -> list[FamilyNotification]:
        members = await self._family_member_repository.get_family_members(session, family_id)

        notifications = []
        for member in members:
            if exclude_user_id and member.user_id == exclude_user_id:
                continue

            notification_data = {
                "user_id": member.user_id,
                "family_id": family_id,
                "type": "product_added",
                "title": "Новый продукт в семье",
                "message": f"Пользователь {added_by_email} добавил продукт '{product_name}' в вашу семью",
                "is_read": False
            }

            notification = await self._notification_repository.create_notification(session, notification_data)
            notifications.append(notification)

        return notifications

    async def create_member_added_notification(
            self,
            session: AsyncSession,
            family_id: UUID,
            new_member_email: str,
            added_by_email: str
    ) -> list[FamilyNotification]:
        members = await self._family_member_repository.get_family_members(session, family_id)

        notifications = []
        for member in members:
            new_user = await self._user_repository.find_by_email(session, new_member_email)
            if new_user and member.user_id == new_user.id:
                notification_data = {
                    "user_id": member.user_id,
                    "family_id": family_id,
                    "type": "member_added",
                    "title": "Добро пожаловать в семью",
                    "message": f"Пользователь {added_by_email} добавил вас в семью",
                    "is_read": False
                }
            else:
                notification_data = {
                    "user_id": member.user_id,
                    "family_id": family_id,
                    "type": "member_added",
                    "title": "Новый участник в семье",
                    "message": f"Пользователь {added_by_email} добавил {new_member_email} в вашу семью",
                    "is_read": False
                }

            notification = await self._notification_repository.create_notification(session, notification_data)
            notifications.append(notification)

        return notifications

    async def create_role_changed_notification(
            self,
            session: AsyncSession,
            user_id: UUID,
            family_id: UUID,
            new_role: str,
            changed_by_email: str
    ) -> FamilyNotification:
        family = await self._family_repository.get_family_by_id(session, family_id)
        family_name = family.name if family else "Семья"

        notification_data = {
            "user_id": user_id,
            "family_id": family_id,
            "type": "role_changed",
            "title": "Изменение роли в семье",
            "message": f"Пользователь {changed_by_email} изменил вашу роль на '{new_role}' в семье '{family_name}'",
            "is_read": False
        }

        return await self._notification_repository.create_notification(session, notification_data)

    async def get_user_notifications(
            self,
            session: AsyncSession,
            user_id: UUID,
            limit: int = 50,
            offset: int = 0,
            is_read: bool | None = None
    ) -> list[FamilyNotificationRead]:
        notifications = await self._notification_repository.get_user_notifications(
            session, user_id, is_read
        )

        result = []
        for notif in notifications:
            stmt = select(FamilyNotification).where(FamilyNotification.id == notif.id).options(
                selectinload(FamilyNotification.user),
                selectinload(FamilyNotification.family),
                selectinload(FamilyNotification.invitation)
            )
            result_notif = await session.execute(stmt)
            loaded_notif = result_notif.scalar_one()
            result.append(convert_family_notification_model_to_schema(loaded_notif))

        return result[offset:offset + limit]

    async def mark_notification_as_read(
            self,
            session: AsyncSession,
            notification_id: UUID,
            user_id: UUID
    ) -> FamilyNotificationRead:
        notification = await self._notification_repository.mark_as_read(
            session, notification_id, user_id
        )

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Уведомление не найдено"
            )

        stmt = select(FamilyNotification).where(FamilyNotification.id == notification.id).options(
            selectinload(FamilyNotification.user),
            selectinload(FamilyNotification.family),
            selectinload(FamilyNotification.invitation)
        )
        result = await session.execute(stmt)
        loaded_notification = result.scalar_one()
        return convert_family_notification_model_to_schema(loaded_notification)

    async def mark_all_notifications_as_read(
            self,
            session: AsyncSession,
            user_id: UUID
    ) -> dict:
        count = await self._notification_repository.mark_all_as_read(session, user_id)

        return {
            "message": f"Отмечено {count} уведомлений как прочитанные",
            "count": count
        }

    async def get_unread_count(
            self,
            session: AsyncSession,
            user_id: UUID
    ) -> dict:
        count = await self._notification_repository.get_unread_count(session, user_id)

        return {
            "unread_count": count
        }

    async def delete_notification(
            self,
            session: AsyncSession,
            notification_id: UUID,
            user_id: UUID
    ) -> None:
        notification = await self._notification_repository.get_notification_by_id(
            session, notification_id
        )

        if not notification or notification.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Уведомление не найдено"
            )

        await self._notification_repository.delete_notification(session, notification_id)

    async def clear_old_notifications(
            self,
            session: AsyncSession,
            days: int = 30
    ) -> dict:
        count = await self._notification_repository.delete_old_notifications(session, days)

        return {
            "message": f"Удалено {count} старых уведомлений",
            "count": count
        }


@dataclass(slots=True)
class FamilyInvitationService:
    _family_invitation_repository: BaseFamilyInvitationRepository
    _family_member_repository: BaseFamilyMemberRepository
    _user_repository: BaseUserRepository
    _notification_service: FamilyNotificationService

    async def get_family_invitations(
            self,
            session: AsyncSession,
            family_id: UUID,
            user_id: UUID
    ) -> list[FamilyInvitationRead]:
        logger.info(f"Getting invitations for family {family_id} by user {user_id}")

        member = await self._family_member_repository.get_family_member(session, family_id, user_id)
        if not member or not member.can_manage_family_products:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view invitations"
            )

        invitations = await self._family_invitation_repository.get_family_invitations(session, family_id)
        result = []
        for inv in invitations:
            stmt = select(FamilyInvitation).where(FamilyInvitation.id == inv.id).options(
                selectinload(FamilyInvitation.inviter),
                selectinload(FamilyInvitation.family)
            )
            result_inv = await session.execute(stmt)
            loaded_inv = result_inv.scalar_one()
            result.append(convert_family_invitation_model_to_schema(loaded_inv))
        return result

    async def get_user_invitations(
            self,
            session: AsyncSession,
            email: str
    ) -> list[FamilyInvitationRead]:
        logger.info(f"Getting invitations for user {email}")
        invitations = await self._family_invitation_repository.get_user_invitations(session, email)
        result = []
        for inv in invitations:
            stmt = select(FamilyInvitation).where(FamilyInvitation.id == inv.id).options(
                selectinload(FamilyInvitation.inviter),
                selectinload(FamilyInvitation.family)
            )
            result_inv = await session.execute(stmt)
            loaded_inv = result_inv.scalar_one()
            result.append(convert_family_invitation_model_to_schema(loaded_inv))
        return result

    async def create_invitation(
            self,
            session: AsyncSession,
            family_id: UUID,
            invitation_data: FamilyInvitationCreate,
            user_id: UUID
    ) -> FamilyInvitationRead:
        logger.info(f"Creating invitation for {invitation_data.email} to family {family_id}")

        member = await self._family_member_repository.get_family_member(session, family_id, user_id)
        if not member or not member.can_manage_family_products:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create invitations"
            )

        try:
            token = str(uuid4())
            expires_at = datetime.now() + timedelta(days=7)

            invitation = await self._family_invitation_repository.create_invitation(session, {
                "family_id": family_id,
                "email": invitation_data.email,
                "invited_by": user_id,
                "role": invitation_data.role,
                "token": token,
                "expires_at": expires_at
            })

            invited_user = await self._user_repository.find_by_email(session, invitation_data.email)

            if invited_user:
                inviter = await self._user_repository.get_by_id(session, user_id)

                await self._notification_service.create_invitation_notification(
                    session=session,
                    user_id=invited_user.id,
                    family_id=family_id,
                    invitation_id=invitation.id,
                    inviter_email=inviter.email if inviter else None,
                    family_name=None
                )

            await session.commit()

            loaded_invitation = await self._family_invitation_repository.get_invitation_by_id(
                session, invitation.id
            )

            if not loaded_invitation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Invitation not found after creation"
                )

            logger.info(f"Invitation created for {invitation_data.email} to family {family_id}")

            return convert_family_invitation_model_to_schema(loaded_invitation)

        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating invitation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create invitation"
            )

    async def accept_invitation(
            self,
            session: AsyncSession,
            token: str,
            user_email: str
    ) -> dict:
        logger.info(f"Accepting invitation with token {token} for user {user_email}")

        invitation = await self._family_invitation_repository.get_invitation_by_token(session, token)
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")

        if invitation.email != user_email:
            raise HTTPException(status_code=403, detail="This invitation is not for you")

        if invitation.status != InvitationStatus.PENDING:
            raise HTTPException(status_code=400, detail="Invitation is not pending")

        if invitation.expires_at < datetime.now():
            await self._family_invitation_repository.update_invitation_status(
                session, invitation, InvitationStatus.EXPIRED
            )
            await session.commit()
            raise HTTPException(status_code=400, detail="Invitation has expired")

        user = await self._user_repository.find_by_email(session, user_email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        existing_member = await self._family_member_repository.get_family_member(
            session, invitation.family_id, user.id
        )
        if existing_member:
            await self._family_invitation_repository.update_invitation_status(
                session, invitation, InvitationStatus.ACCEPTED
            )
            await session.commit()
            raise HTTPException(status_code=400, detail="User is already a member of this family")

        await self._family_member_repository.add_member(session, {
            "family_id": invitation.family_id,
            "user_id": user.id,
            "role": invitation.role
        })

        await self._family_invitation_repository.update_invitation_status(
            session, invitation, InvitationStatus.ACCEPTED
        )

        inviter = await self._user_repository.get_by_id(session, invitation.invited_by)

        await self._notification_service.create_member_added_notification(
            session=session,
            family_id=invitation.family_id,
            new_member_email=user_email,
            added_by_email=inviter.email if inviter else "неизвестный"
        )

        await session.commit()
        logger.info(f"Invitation accepted for user {user_email}")

        return {"message": "Invitation accepted successfully"}

    async def decline_invitation(
            self,
            session: AsyncSession,
            token: str,
            user_email: str
    ) -> dict:
        logger.info(f"Declining invitation with token {token} for user {user_email}")

        invitation = await self._family_invitation_repository.get_invitation_by_token(session, token)
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")

        if invitation.email != user_email:
            raise HTTPException(status_code=403, detail="This invitation is not for you")

        if invitation.status != InvitationStatus.PENDING:
            raise HTTPException(status_code=400, detail="Invitation is not pending")

        await self._family_invitation_repository.update_invitation_status(
            session, invitation, InvitationStatus.DECLINED
        )

        await session.commit()
        logger.info(f"Invitation declined for user {user_email}")

        return {"message": "Invitation declined successfully"}

    async def cancel_invitation(
            self,
            session: AsyncSession,
            invitation_id: UUID,
            user_id: UUID
    ) -> dict:
        logger.info(f"Canceling invitation {invitation_id} by user {user_id}")

        invitation = await self._family_invitation_repository.get_invitation_by_id(session, invitation_id)
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")

        member = await self._family_member_repository.get_family_member(session, invitation.family_id, user_id)
        if not member or not member.can_manage_family_products:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to cancel invitation"
            )

        try:
            await self._family_invitation_repository.delete_invitation(session, invitation)
            await session.commit()
            logger.info(f"Invitation {invitation_id} canceled")
            return {"message": "Invitation canceled successfully"}

        except Exception as e:
            await session.rollback()
            logger.error(f"Error canceling invitation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel invitation"
            )
