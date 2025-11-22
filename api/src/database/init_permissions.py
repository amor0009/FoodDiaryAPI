import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.src.database.database import async_session_maker
from api.src.models.base import generate_uuid
from api.src.models.staff import Permission, Role, Staff

from api.src.core.security import Security
from datetime import datetime


async def init_permissions_and_roles(db: AsyncSession):
    """Инициализация прав доступа и ролей"""

    # Создаем права доступа
    permissions_data = [
        {
            "title": "admin:full_access",
            "description": "Полный доступ ко всем функциям администратора"
        },
        {
            "title": "staff:view",
            "description": "Просмотр сотрудников"
        },
        {
            "title": "staff:create",
            "description": "Создание сотрудников"
        },
        {
            "title": "staff:edit",
            "description": "Редактирование сотрудников"
        },
        {
            "title": "staff:delete",
            "description": "Удаление сотрудников"
        },
        {
            "title": "roles:view",
            "description": "Просмотр ролей"
        },
        {
            "title": "roles:create",
            "description": "Создание ролей"
        },
        {
            "title": "roles:edit",
            "description": "Редактирование ролей"
        },
        {
            "title": "roles:delete",
            "description": "Удаление ролей"
        },
        {
            "title": "permissions:view",
            "description": "Просмотр прав доступа"
        },
        {
            "title": "users:view",
            "description": "Просмотр пользователей"
        },
        {
            "title": "users:create",
            "description": "Создание пользователей"
        },
        {
            "title": "users:edit",
            "description": "Редактирование пользователей"
        },
        {
            "title": "users:delete",
            "description": "Удаление пользователей"
        },
        {
            "title": "products:view",
            "description": "Просмотр продуктов"
        },
        {
            "title": "products:create",
            "description": "Создание продуктов"
        },
        {
            "title": "products:edit",
            "description": "Редактирование продуктов"
        },
        {
            "title": "products:delete",
            "description": "Удаление продуктов"
        },
        {
            "title": "meals:view",
            "description": "Просмотр приемов пищи"
        },
        {
            "title": "meals:create",
            "description": "Создание приемов пищи"
        },
        {
            "title": "meals:edit",
            "description": "Редактирование приемов пищи"
        },
        {
            "title": "meals:delete",
            "description": "Удаление приемов пищи"
        },
        {
            "title": "user_weights:view",
            "description": "Просмотр весов пользователей"
        },
        {
            "title": "user_weights:create",
            "description": "Создание записей веса"
        },
        {
            "title": "user_weights:edit",
            "description": "Редактирование записей веса"
        },
        {
            "title": "user_weights:delete",
            "description": "Удаление записей веса"
        },
        {
            "title": "meal_products:view",
            "description": "Просмотр связей продуктов и приемов пищи"
        },
        {
            "title": "meal_products:create",
            "description": "Создание связей продуктов и приемов пищи"
        },
        {
            "title": "meal_products:edit",
            "description": "Редактирование связей продуктов и приемов пищи"
        },
        {
            "title": "meal_products:delete",
            "description": "Удаление связей продуктов и приемов пищи"
        }
    ]

    permissions_map = {}

    for perm_data in permissions_data:
        stmt = select(Permission).where(Permission.title == perm_data["title"])
        result = await db.execute(stmt)
        existing_perm = result.scalar_one_or_none()

        if not existing_perm:
            permission = Permission(
                id=generate_uuid(),
                title=perm_data["title"],
                description=perm_data["description"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()  # Добавлено поле updated_at
            )
            db.add(permission)
            permissions_map[perm_data["title"]] = permission
            print(f"Created permission: {perm_data['title']}")
        else:
            permissions_map[perm_data["title"]] = existing_perm
            print(f"Permission already exists: {perm_data['title']}")

    await db.commit()

    # Создаем роли
    roles_data = [
        {
            "title": "Администратор",
            "permissions": [p for p in permissions_map.keys()]  # Все права
        },
        {
            "title": "Генеральный менеджер",
            "permissions": [
                "staff:view",
                "users:view",
                "users:create",
                "users:edit",
                "products:view",
                "products:create",
                "products:edit",
                "meals:view",
                "user_weights:view",
                "meal_products:view"
            ]
        },
        {
            "title": "Контент-менеджер",
            "permissions": [
                "products:view",
                "products:create",
                "products:edit",
                "products:delete",
                "meals:view",
                "meal_products:view"
            ]
        },
        {
            "title": "Менеджер поддержки",
            "permissions": [
                "users:view",
                "users:create",
                "users:edit",
                "meals:view",
                "user_weights:view"
            ]
        }
    ]

    roles_map = {}

    for role_data in roles_data:
        # Проверяем, существует ли уже такая роль
        stmt = select(Role).where(Role.title == role_data["title"])
        result = await db.execute(stmt)
        existing_role = result.scalar_one_or_none()

        if not existing_role:
            role = Role(
                id=generate_uuid(),
                title=role_data["title"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()  # Добавлено поле updated_at
            )
            # Добавляем права к роли
            for perm_title in role_data["permissions"]:
                if perm_title in permissions_map:
                    role.permissions.append(permissions_map[perm_title])

            db.add(role)
            roles_map[role_data["title"]] = role
            print(f"Created role: {role_data['title']} with {len(role_data['permissions'])} permissions")
        else:
            roles_map[role_data["title"]] = existing_role
            print(f"Role already exists: {role_data['title']}")

    await db.commit()

    return roles_map


async def create_admin_user(db: AsyncSession, roles_map):
    """Создание администратора"""

    # Проверяем, существует ли уже администратор
    stmt = select(Staff).where(Staff.login == "admin@fooddiary.com")
    result = await db.execute(stmt)
    existing_admin = result.scalar_one_or_none()

    if not existing_admin:
        admin_role = roles_map.get("Администратор")
        if not admin_role:
            print("Admin role not found!")
            return

        admin_user = Staff(
            id=generate_uuid(),
            login="admin@fooddiary.com",
            email="admin@fooddiary.com",
            name="Администратор Системы",
            hashed_password=Security.get_password_hash("admin123"),
            role_id=admin_role.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()  # Добавлено поле updated_at
        )

        db.add(admin_user)
        await db.commit()
        print("Created admin user: admin@fooddiary.com / admin123")
    else:
        print("Admin user already exists")


async def main():
    """Основная функция инициализации"""
    async with async_session_maker() as session:
        try:
            print("Starting permissions and roles initialization...")

            # Инициализируем права и роли
            roles_map = await init_permissions_and_roles(session)

            # Создаем администратора
            await create_admin_user(session, roles_map)

            print("Initialization completed successfully!")

        except Exception as e:
            await session.rollback()
            print(f"Error during initialization: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
