from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr
from api.src.models.family import FamilyRole, InvitationStatus


class FamilyRead(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    is_active: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    members_count: int = 0
    products_count: int = 0

    class Config:
        from_attributes = True


class FamilyCreate(BaseModel):
    name: str
    description: str | None = None


class FamilyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class FamilyMemberRead(BaseModel):
    id: UUID
    family_id: UUID
    user_id: UUID
    role: FamilyRole
    created_at: datetime
    updated_at: datetime
    user_email: str
    user_firstname: str | None = None
    user_lastname: str | None = None
    can_manage_family_products: bool
    can_edit_family_product: bool = False  # Для конкретного продукта

    class Config:
        from_attributes = True


class FamilyMemberCreate(BaseModel):
    user_id: UUID
    role: FamilyRole = FamilyRole.MEMBER


class FamilyMemberUpdate(BaseModel):
    role: FamilyRole | None = None


class FamilyMemberRoleUpdate(BaseModel):
    role: FamilyRole

    class Config:
        from_attributes = True


class FamilyProductRead(BaseModel):
    id: UUID
    family_id: UUID
    product_id: UUID
    added_by: UUID
    created_at: datetime
    updated_at: datetime
    product_name: str
    product_weight: float
    product_calories: float
    added_by_email: str
    can_edit: bool = False
    can_delete: bool = False

    class Config:
        from_attributes = True


class FamilyProductCreate(BaseModel):
    product_id: UUID


class FamilyInvitationRead(BaseModel):
    id: UUID
    family_id: UUID
    email: EmailStr
    invited_by: UUID
    role: FamilyRole
    status: InvitationStatus
    token: str
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    family_name: str
    inviter_email: str

    class Config:
        from_attributes = True


class FamilyInvitationCreate(BaseModel):
    email: EmailStr
    role: FamilyRole = FamilyRole.MEMBER


class FamilyInvitationUpdate(BaseModel):
    status: InvitationStatus


class FamilyNotificationBase(BaseModel):
    type: str
    title: str
    message: str
    is_read: bool = False
    read_at: datetime | None = None
    family_id: UUID
    invitation_id: UUID | None = None


class FamilyNotificationCreate(FamilyNotificationBase):
    user_id: UUID


class FamilyNotificationUpdate(BaseModel):
    is_read: bool | None = None


class FamilyNotificationRead(FamilyNotificationBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    family_name: str | None = None
    inviter_email: str | None = None

    class Config:
        from_attributes = True
