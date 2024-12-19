from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.schemas.user import UserUpdate
from src.schemas.user_weight import UserWeightUpdate
from src.services.user_weight_service import save_or_update_weight


async def find_user_by_login_and_email(db: AsyncSession, email_login: str):
    query = select(User).where(or_(User.login == email_login, User.email == email_login))
    result = await db.execute(query)
    return result.scalars().first()


async def delete_user(db: AsyncSession, user: User):
    await db.delete(user)
    await db.commit()
    return user


async def update_user(user_update: UserUpdate, db: AsyncSession, current_user: User):
    user = await find_user_by_login_and_email(db, current_user.login)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user_update.firstname is not None:
        user.firstname = user_update.firstname
    if user_update.lastname is not None:
        user.lastname = user_update.lastname
    if user_update.age is not None:
        user.age = user_update.age
    if user_update.height is not None:
        user.height = user_update.height
    if user_update.weight is not None:
        user.weight = user_update.weight
    if user_update.gender is not None:
        user.gender = user_update.gender
    if user_update.aim is not None:
        user.aim = user_update.aim
    if user_update.recommended_calories is not None:
        user.recommended_calories = user_update.recommended_calories
    if user_update.profile_image is not None:
        user.profile_image = user_update.profile_image

    if user.weight:
        user_weight = UserWeightUpdate(
            user_id=user.id,
            weight=user.weight,
        )
        await save_or_update_weight(user_weight, db, current_user)
    await db.commit()
    await db.refresh(user)
    return user
