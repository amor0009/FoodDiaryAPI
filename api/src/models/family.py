from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.ext.hybrid import hybrid_property
from jinja2 import Template

from api.src.models.base import Base


if TYPE_CHECKING:
    from api.src.models.user import User
    from api.src.models.product import Product


class FamilyRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"

    @classmethod
    def get_admin_choices(cls):
        return [
            (cls.OWNER.value, "Владелец"),
            (cls.ADMIN.value, "Администратор"),
            (cls.MEMBER.value, "Участник"),
        ]


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class Family(Base):
    __tablename__ = "families"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("user.id"), nullable=False)

    creator: Mapped["User"] = relationship("User", back_populates="created_families")
    members: Mapped[list["FamilyMember"]] = relationship(
        "FamilyMember", back_populates="family", cascade="all, delete-orphan"
    )
    shared_products: Mapped[list["FamilyProduct"]] = relationship(
        "FamilyProduct", back_populates="family", cascade="all, delete-orphan"
    )
    invitations: Mapped[list["FamilyInvitation"]] = relationship(
        "FamilyInvitation", back_populates="family", cascade="all, delete-orphan"
    )

    async def __admin_select2_repr__(self, request):
        return Template(
            "<span><strong>Название:</strong> {{ obj.name }}</span>"
            "<span><strong> Создатель:</strong> {{ obj.creator.email if obj.creator else 'Неизвестно' }}</span>",
            autoescape=True,
        ).render(obj=self)

    async def __admin_repr__(self, request):
        return f"Семья: {self.name}"


class FamilyMember(Base):
    __tablename__ = "family_members"

    family_id: Mapped[UUID] = mapped_column(ForeignKey("families.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"), nullable=False)
    role: Mapped[FamilyRole] = mapped_column(SQLEnum(FamilyRole), default=FamilyRole.MEMBER)

    family: Mapped["Family"] = relationship("Family", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="family_memberships")

    @hybrid_property
    def can_manage_family_products(self) -> bool:
        return self.role in [FamilyRole.OWNER, FamilyRole.ADMIN]

    @hybrid_property
    def can_view_family_products(self) -> bool:
        return True

    @hybrid_property
    def can_add_family_products(self) -> bool:
        return True

    def can_edit_family_product(self, family_product: "FamilyProduct") -> bool:
        if self.can_manage_family_products:
            return True
        return family_product.added_by == self.user_id

    def can_delete_family_product(self, family_product: "FamilyProduct") -> bool:
        return self.can_edit_family_product(family_product)

    async def __admin_repr__(self, request):
        return f"Участник: {self.user.email} в {self.family.name}"


class FamilyInvitation(Base):
    __tablename__ = "family_invitations"

    family_id: Mapped[UUID] = mapped_column(ForeignKey("families.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    invited_by: Mapped[UUID] = mapped_column(ForeignKey("user.id"), nullable=False)
    role: Mapped[FamilyRole] = mapped_column(SQLEnum(FamilyRole), default=FamilyRole.MEMBER)
    status: Mapped[InvitationStatus] = mapped_column(SQLEnum(InvitationStatus), default=InvitationStatus.PENDING)
    token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    family: Mapped["Family"] = relationship("Family", back_populates="invitations")
    inviter: Mapped["User"] = relationship("User", foreign_keys=[invited_by])

    async def __admin_repr__(self, request):
        return f"Для {self.email} в {self.family.name}"


class FamilyProduct(Base):
    __tablename__ = "family_products"

    family_id: Mapped[UUID] = mapped_column(ForeignKey("families.id"), nullable=False)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("product.id"), nullable=False)
    added_by: Mapped[UUID] = mapped_column(ForeignKey("user.id"), nullable=False)

    family: Mapped["Family"] = relationship("Family", back_populates="shared_products")
    product: Mapped["Product"] = relationship("Product", back_populates="family_shares")
    added_by_user: Mapped["User"] = relationship("User", foreign_keys=[added_by])

    def can_edit(self, user_id: UUID) -> bool:
        return self.added_by == user_id

    def can_manage(self, family_member: "FamilyMember") -> bool:
        if family_member.can_manage_family_products:
            return True
        return self.added_by == family_member.user_id

    async def __admin_repr__(self, request):
        return f"Продукт {self.product.name} в семье {self.family.name}"


class FamilyNotification(Base):
    __tablename__ = "family_notifications"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"), nullable=False)
    family_id: Mapped[UUID] = mapped_column(ForeignKey("families.id"), nullable=False)
    invitation_id: Mapped[UUID | None] = mapped_column(ForeignKey("family_invitations.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", backref="family_notifications")
    family: Mapped["Family"] = relationship("Family", foreign_keys=[family_id])
    invitation: Mapped["FamilyInvitation"] = relationship("FamilyInvitation", foreign_keys=[invitation_id])

    async def __admin_repr__(self, request):
        return f"Для {self.user.email}: {self.title}"
