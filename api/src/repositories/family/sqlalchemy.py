from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import select, and_, or_, delete, func, update
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models.family import Family, FamilyMember, FamilyInvitation, InvitationStatus, FamilyRole, FamilyProduct, \
    FamilyNotification
from api.src.repositories.crud import CrudOperations
from api.src.repositories.family.base import BaseFamilyRepository, BaseFamilyInvitationRepository, \
    BaseFamilyMemberRepository, BaseFamilyProductRepository, BaseFamilyNotificationRepository


@dataclass(slots=True)
class SqlAlchemyFamilyRepository(BaseFamilyRepository):
    def __init__(self) -> None:
        self._crud = CrudOperations(Family)

    async def create_family(self, session: AsyncSession, family_data: dict) -> Family:
        family = Family(**family_data)
        return await self._crud.insert(session, family)

    async def get_family_by_id(self, session: AsyncSession, family_id: UUID) -> Family | None:
        result = await session.execute(
            select(Family)
            .options(joinedload(Family.members), joinedload(Family.shared_products))
            .where(Family.id == family_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_user_families(self, session: AsyncSession, user_id: UUID) -> list[Family]:
        created_families_result = await session.execute(
            select(Family)
            .options(joinedload(Family.members), joinedload(Family.shared_products))
            .where(Family.created_by == user_id)
        )

        member_families_result = await session.execute(
            select(Family)
            .options(joinedload(Family.members), joinedload(Family.shared_products))
            .join(FamilyMember)
            .where(
                FamilyMember.user_id == user_id,
                Family.is_active == True
            )
        )

        created_families = created_families_result.unique().scalars().all()
        member_families = member_families_result.unique().scalars().all()

        # Объединяем и удаляем дубликаты по ID
        all_families = list(created_families) + list(member_families)
        unique_families = {family.id: family for family in all_families}.values()
        return list(unique_families)

    async def update_family(self, session: AsyncSession, family: Family, update_data: dict) -> Family:
        for key, value in update_data.items():
            setattr(family, key, value)
        await session.commit()
        await session.refresh(family)
        return family

    async def delete_family(self, session: AsyncSession, family: Family) -> Family:
        await self._crud.delete(session, family.id)
        await session.commit()
        return family


@dataclass(slots=True)
class SqlAlchemyFamilyInvitationRepository(BaseFamilyInvitationRepository):
    def __init__(self) -> None:
        self._crud = CrudOperations(FamilyInvitation)

    async def create_invitation(self, session: AsyncSession, invitation_data: dict) -> FamilyInvitation:
        invitation = FamilyInvitation(**invitation_data)
        db_invitation = await self._crud.insert(session, invitation)
        return db_invitation

    async def get_invitation_by_token(self, session: AsyncSession, token: str) -> FamilyInvitation | None:
        result = await session.execute(
            select(FamilyInvitation)
            .options(joinedload(FamilyInvitation.family), joinedload(FamilyInvitation.inviter))
            .where(FamilyInvitation.token == token)
        )
        return result.scalar_one_or_none()

    async def get_invitation_by_id(self, session: AsyncSession, invitation_id: UUID) -> FamilyInvitation | None:
        result = await session.execute(
            select(FamilyInvitation)
            .options(joinedload(FamilyInvitation.family), joinedload(FamilyInvitation.inviter))
            .where(FamilyInvitation.id == invitation_id)
        )
        return result.scalar_one_or_none()

    async def get_family_invitations(self, session: AsyncSession, family_id: UUID) -> list[FamilyInvitation]:
        result = await session.execute(
            select(FamilyInvitation)
            .options(joinedload(FamilyInvitation.family), joinedload(FamilyInvitation.inviter))
            .where(
                FamilyInvitation.family_id == family_id,
                FamilyInvitation.status == InvitationStatus.PENDING
            )
        )
        return list(result.scalars().all())

    async def get_user_invitations(self, session: AsyncSession, email: str) -> list[FamilyInvitation]:
        result = await session.execute(
            select(FamilyInvitation)
            .options(joinedload(FamilyInvitation.family), joinedload(FamilyInvitation.inviter))
            .where(
                FamilyInvitation.email == email,
                FamilyInvitation.status == InvitationStatus.PENDING
            )
        )
        return list(result.scalars().all())

    async def update_invitation_status(self, session: AsyncSession, invitation: FamilyInvitation, status: InvitationStatus) -> FamilyInvitation:
        invitation.status = status
        await session.commit()
        await session.refresh(invitation)
        return invitation

    async def delete_invitation(self, session: AsyncSession, invitation: FamilyInvitation) -> None:
        await self._crud.delete(session, invitation.id)


@dataclass(slots=True)
class SqlAlchemyFamilyMemberRepository(BaseFamilyMemberRepository):
    def __init__(self) -> None:
        self._crud = CrudOperations(FamilyMember)

    async def add_member(self, session: AsyncSession, member_data: dict) -> FamilyMember:
        member = FamilyMember(**member_data)
        return await self._crud.insert(session, member)

    async def get_family_members(self, session: AsyncSession, family_id: UUID) -> list[FamilyMember]:
        result = await session.execute(
            select(FamilyMember)
            .options(joinedload(FamilyMember.user))
            .where(FamilyMember.family_id == family_id)
        )
        return list(result.scalars().all())

    async def get_user_memberships(self, session: AsyncSession, user_id: UUID) -> list[FamilyMember]:
        result = await session.execute(
            select(FamilyMember)
            .options(joinedload(FamilyMember.family), joinedload(FamilyMember.user))
            .where(FamilyMember.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_family_member(self, session: AsyncSession, family_id: UUID, user_id: UUID) -> FamilyMember | None:
        result = await session.execute(
            select(FamilyMember)
            .options(joinedload(FamilyMember.user))
            .where(
                FamilyMember.family_id == family_id,
                FamilyMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def update_member_role(self, session: AsyncSession, member: FamilyMember, new_role: FamilyRole) -> FamilyMember:
        member.role = new_role
        await session.commit()
        await session.refresh(member)
        return member

    async def remove_member(self, session: AsyncSession, member: FamilyMember) -> None:
        await self._crud.delete(session, member.id)


@dataclass(slots=True)
class SqlAlchemyFamilyProductRepository(BaseFamilyProductRepository):
    def __init__(self) -> None:
        self._crud = CrudOperations(FamilyProduct)

    async def add_product_to_family(self, session: AsyncSession, family_product_data: dict) -> FamilyProduct:
        family_product = FamilyProduct(**family_product_data)
        return await self._crud.insert(session, family_product)

    async def get_family_products(self, session: AsyncSession, family_id: UUID) -> list[FamilyProduct]:
        result = await session.execute(
            select(FamilyProduct)
            .options(joinedload(FamilyProduct.product), joinedload(FamilyProduct.added_by_user))
            .where(FamilyProduct.family_id == family_id)
        )
        return list(result.scalars().all())

    async def get_family_product(self, session: AsyncSession, family_id: UUID, product_id: UUID) -> FamilyProduct | None:
        result = await session.execute(
            select(FamilyProduct)
            .options(joinedload(FamilyProduct.product), joinedload(FamilyProduct.added_by_user))
            .where(
                FamilyProduct.family_id == family_id,
                FamilyProduct.product_id == product_id
            )
        )
        return result.scalar_one_or_none()

    async def get_user_added_family_products(self, session: AsyncSession, user_id: UUID) -> list[FamilyProduct]:
        result = await session.execute(
            select(FamilyProduct)
            .options(joinedload(FamilyProduct.product), joinedload(FamilyProduct.family))
            .where(FamilyProduct.added_by == user_id)
        )
        return list(result.scalars().all())

    async def remove_product_from_family(self, session: AsyncSession, family_product: FamilyProduct) -> None:
        await self._crud.delete(session, family_product.id)

    async def is_product_in_family(self, session: AsyncSession, family_id: UUID, product_id: UUID) -> bool:
        result = await session.execute(
            select(FamilyProduct).where(
                FamilyProduct.family_id == family_id,
                FamilyProduct.product_id == product_id
            )
        )
        return result.scalar_one_or_none() is not None


@dataclass(slots=True)
class SqlAlchemyFamilyNotificationRepository(BaseFamilyNotificationRepository):
    def __init__(self) -> None:
        self._crud = CrudOperations(FamilyNotification)

    async def create_notification(self, session: AsyncSession, notification_data: dict) -> FamilyNotification:
        notification = FamilyNotification(**notification_data)
        return await self._crud.insert(session, notification)

    async def get_notification_by_id(self, session: AsyncSession, notification_id: UUID) -> FamilyNotification | None:
        result = await session.execute(
            select(FamilyNotification)
            .options(joinedload(FamilyNotification.family), joinedload(FamilyNotification.invitation))
            .where(FamilyNotification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def get_user_notifications(self, session: AsyncSession, user_id: UUID, is_read: bool | None = None) -> list[FamilyNotification]:
        query = select(FamilyNotification).options(
            joinedload(FamilyNotification.family),
            joinedload(FamilyNotification.invitation).joinedload(FamilyInvitation.inviter)
        ).where(FamilyNotification.user_id == user_id)

        if is_read is not None:
            query = query.where(FamilyNotification.is_read == is_read)

        query = query.order_by(FamilyNotification.created_at.desc())

        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_family_notifications(self, session: AsyncSession, family_id: UUID) -> list[FamilyNotification]:
        result = await session.execute(
            select(FamilyNotification)
            .options(joinedload(FamilyNotification.user))
            .where(FamilyNotification.family_id == family_id)
            .order_by(FamilyNotification.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_as_read(self, session: AsyncSession, notification_id: UUID,
                           user_id: UUID) -> FamilyNotification | None:
        notification = await self.get_notification_by_id(session, notification_id)

        if not notification or notification.user_id != user_id:
            return None

        notification.is_read = True
        notification.read_at = datetime.now()

        await session.commit()
        await session.refresh(notification)
        return notification

    async def mark_all_as_read(self, session: AsyncSession, user_id: UUID) -> int:
        result = await session.execute(
            update(FamilyNotification)
            .where(
                FamilyNotification.user_id == user_id,
                FamilyNotification.is_read == False
            )
            .values(is_read=True, read_at=datetime.now())
            .returning(FamilyNotification.id)
        )

        updated_count = len(result.scalars().all())
        await session.commit()
        return updated_count

    async def delete_notification(self, session: AsyncSession, notification_id: UUID) -> None:
        await self._crud.delete(session, notification_id)

    async def delete_old_notifications(self, session: AsyncSession, days: int = 30) -> int:
        cutoff_date = datetime.now() - timedelta(days=days)

        result = await session.execute(
            delete(FamilyNotification)
            .where(FamilyNotification.created_at < cutoff_date)
            .returning(FamilyNotification.id)
        )

        deleted_count = len(result.scalars().all())
        await session.commit()
        return deleted_count

    async def get_unread_count(self, session: AsyncSession, user_id: UUID) -> int:
        result = await session.execute(
            select(func.count(FamilyNotification.id))
            .where(
                FamilyNotification.user_id == user_id,
                FamilyNotification.is_read == False
            )
        )
        return result.scalar_one() or 0
