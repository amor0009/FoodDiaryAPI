from abc import ABC, abstractmethod
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.models.family import Family, FamilyMember, FamilyProduct, FamilyInvitation, InvitationStatus, FamilyRole, \
    FamilyNotification


class BaseFamilyRepository(ABC):
    @abstractmethod
    async def create_family(self, session: AsyncSession, family_data: dict) -> Family: ...

    @abstractmethod
    async def get_family_by_id(self, session: AsyncSession, family_id: UUID) -> Family | None: ...

    @abstractmethod
    async def get_user_families(self, session: AsyncSession, user_id: UUID) -> list[Family]: ...

    @abstractmethod
    async def update_family(self, session: AsyncSession, family: Family, update_data: dict) -> Family: ...

    @abstractmethod
    async def delete_family(self, session: AsyncSession, family: Family) -> None: ...


class BaseFamilyInvitationRepository(ABC):
    @abstractmethod
    async def create_invitation(self, session: AsyncSession, invitation_data: dict) -> FamilyInvitation: ...

    @abstractmethod
    async def get_invitation_by_id(self, session: AsyncSession, invitation_id: UUID) -> FamilyInvitation | None: ...

    @abstractmethod
    async def get_invitation_by_token(self, session: AsyncSession, token: str) -> FamilyInvitation | None: ...

    @abstractmethod
    async def get_family_invitations(self, session: AsyncSession, family_id: UUID) -> list[FamilyInvitation]: ...

    @abstractmethod
    async def get_user_invitations(self, session: AsyncSession, email: str) -> list[FamilyInvitation]: ...

    @abstractmethod
    async def update_invitation_status(self, session: AsyncSession, invitation: FamilyInvitation,
                                       status: InvitationStatus) -> FamilyInvitation: ...

    @abstractmethod
    async def delete_invitation(self, session: AsyncSession, invitation: FamilyInvitation) -> None: ...


class BaseFamilyMemberRepository(ABC):
    @abstractmethod
    async def add_member(self, session: AsyncSession, member_data: dict) -> FamilyMember: ...

    @abstractmethod
    async def get_family_members(self, session: AsyncSession, family_id: UUID) -> list[FamilyMember]: ...

    @abstractmethod
    async def get_user_memberships(self, session: AsyncSession, user_id: UUID) -> list[FamilyMember]: ...

    @abstractmethod
    async def get_family_member(self, session: AsyncSession, family_id: UUID, user_id: UUID) -> FamilyMember | None: ...

    @abstractmethod
    async def update_member_role(self, session: AsyncSession, member: FamilyMember,
                                 new_role: FamilyRole) -> FamilyMember: ...

    @abstractmethod
    async def remove_member(self, session: AsyncSession, member: FamilyMember) -> None: ...


class BaseFamilyProductRepository(ABC):
    @abstractmethod
    async def add_product_to_family(self, session: AsyncSession, family_product_data: dict) -> FamilyProduct: ...

    @abstractmethod
    async def get_family_products(self, session: AsyncSession, family_id: UUID) -> list[FamilyProduct]: ...

    @abstractmethod
    async def get_family_product(self, session: AsyncSession, family_id: UUID,
                                 product_id: UUID) -> FamilyProduct | None: ...

    @abstractmethod
    async def get_user_added_family_products(self, session: AsyncSession, user_id: UUID) -> list[FamilyProduct]: ...

    @abstractmethod
    async def remove_product_from_family(self, session: AsyncSession, family_product: FamilyProduct) -> None: ...

    @abstractmethod
    async def is_product_in_family(self, session: AsyncSession, family_id: UUID, product_id: UUID) -> bool: ...


class BaseFamilyNotificationRepository(ABC):
    @abstractmethod
    async def create_notification(self, session: AsyncSession, notification_data: dict) -> FamilyNotification: ...

    @abstractmethod
    async def get_notification_by_id(self, session: AsyncSession,
                                     notification_id: UUID) -> FamilyNotification | None: ...

    @abstractmethod
    async def get_user_notifications(self, session: AsyncSession, user_id: UUID, is_read: bool | None = None) -> list[
        FamilyNotification]: ...

    @abstractmethod
    async def get_family_notifications(self, session: AsyncSession, family_id: UUID) -> list[FamilyNotification]: ...

    @abstractmethod
    async def mark_as_read(self, session: AsyncSession, notification_id: UUID,
                           user_id: UUID) -> FamilyNotification | None: ...

    @abstractmethod
    async def mark_all_as_read(self, session: AsyncSession, user_id: UUID) -> int: ...

    @abstractmethod
    async def delete_notification(self, session: AsyncSession, notification_id: UUID) -> None: ...

    @abstractmethod
    async def delete_old_notifications(self, session: AsyncSession, days: int = 30) -> int: ...

    @abstractmethod
    async def get_unread_count(self, session: AsyncSession, user_id: UUID) -> int: ...
