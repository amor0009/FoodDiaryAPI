from enum import Enum
from sqlalchemy import String, ForeignKey, Table, Column, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from api.src.models.base import Base


role_permissions_table = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id"), primary_key=True),
)


class PermissionsEnum(str, Enum):
    ADMIN_FULL_ACCESS = "admin:full_access"

    STAFF_VIEW = "staff:view"
    STAFF_CREATE = "staff:create"
    STAFF_EDIT = "staff:edit"
    STAFF_DELETE = "staff:delete"

    ROLES_VIEW = "roles:view"
    ROLES_CREATE = "roles:create"
    ROLES_EDIT = "roles:edit"
    ROLES_DELETE = "roles:delete"

    PERMISSIONS_VIEW = "permissions:view"

    USERS_VIEW = "users:view"
    USERS_CREATE = "users:create"
    USERS_EDIT = "users:edit"
    USERS_DELETE = "users:delete"

    PRODUCTS_VIEW = "products:view"
    PRODUCTS_CREATE = "products:create"
    PRODUCTS_EDIT = "products:edit"
    PRODUCTS_DELETE = "products:delete"

    MEALS_VIEW = "meals:view"
    MEALS_CREATE = "meals:create"
    MEALS_EDIT = "meals:edit"
    MEALS_DELETE = "meals:delete"

    USER_WEIGHTS_VIEW = "user_weights:view"
    USER_WEIGHTS_CREATE = "user_weights:create"
    USER_WEIGHTS_EDIT = "user_weights:edit"
    USER_WEIGHTS_DELETE = "user_weights:delete"

    MEAL_PRODUCTS_VIEW = "meal_products:view"
    MEAL_PRODUCTS_CREATE = "meal_products:create"
    MEAL_PRODUCTS_EDIT = "meal_products:edit"
    MEAL_PRODUCTS_DELETE = "meal_products:delete"


class Permission(Base):
    __tablename__ = "permissions"

    title: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=role_permissions_table,
        back_populates="permissions"
    )

    async def __admin_select2_repr__(self, request):
        return f"<span><strong>Название:</strong> {self.title} <strong>Описание:</strong> {self.description}</span>"

    async def __admin_repr__(self, request):
        return self.description


class Role(Base):
    __tablename__ = "roles"

    title: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary=role_permissions_table,
        back_populates="roles"
    )

    staff_users: Mapped[list["Staff"]] = relationship("Staff", back_populates="role")

    async def __admin_select2_repr__(self, request):
        return f"<span><strong>Название:</strong> {self.title}</span>"

    async def __admin_repr__(self, request):
        return self.title


class Staff(Base):
    __tablename__ = "staff"

    login: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(100), nullable=False)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    role: Mapped["Role"] = relationship("Role", back_populates="staff_users")

    async def __admin_repr__(self, request):
        return self.login
