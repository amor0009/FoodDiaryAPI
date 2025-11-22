from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from api.src.core.security import Security
from api.src.database.database import get_async_session
from api.src.models.user import User
from api.src.schemas.user import UserUpdate, UserCalculateNutrients, UserRead, EmailChangeConfirm, CheckForgotPassword, \
    UpdateForgotPassword, UpdatePassword
from api.src.services.user import UserService
from api.src.dependencies.services import get_user_service


user_router = APIRouter(prefix="/api/users", tags=["users"])


@user_router.delete("/me")
async def delete_current_user(
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
) -> None:
    await user_service.delete_user(session, current_user)
    return None


@user_router.get("/me")
async def get_current_user_data(
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    user = await user_service.find_user_by_login_and_email(session, current_user.login)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@user_router.get("/find/{login_email}")
async def find_user(
    login_email: str,
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    user = await user_service.find_user_by_login_and_email(session, login_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@user_router.put("/me")
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
) -> UserRead:
    return await user_service.update_user(session, user_update, current_user)


@user_router.post("/me/calculate-nutrients")
async def calculate_nutrients_for_authenticated_users(
    current_user: User = Depends(Security.get_required_user),
    user_service: UserService = Depends(get_user_service),
    session: AsyncSession = Depends(get_async_session),
    target_weight: float | None = None,
    target_days: int | None = None,
) -> dict:
    user_data = UserCalculateNutrients.model_validate(current_user)
    return await user_service.calculate_nutrients(session, user_data, current_user, target_weight, target_days,)


@user_router.post("/calculate-nutrients")
async def calculate_nutrients_for_all_users(
    user_data: UserCalculateNutrients,
    user_service: UserService = Depends(get_user_service),
) -> dict:
    return await user_service.calculate_nutrients_basic(user_data)


@user_router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(Security.get_required_user),
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
) -> dict:
    return await user_service.upload_avatar(session, file, current_user)


@user_router.get("/avatar")
async def get_avatar(
    current_user: User = Depends(Security.get_required_user),
    user_service: UserService = Depends(get_user_service),
) -> dict:
    return await user_service.get_avatar(current_user)


@user_router.post("/me/email")
async def start_email_change(
    email: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(Security.get_required_user),
    user_service: UserService = Depends(get_user_service)
) -> str:
    await user_service.start_email_change(session, email)
    return f"Message with code is sent to your email address: {current_user.email}"


@user_router.patch("/me/email/final")
async def final_email_change(
    user_data: EmailChangeConfirm,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(Security.get_required_user)
) -> UserRead:
    updated_user = await user_service.final_email_change(session, response, current_user.id, user_data)
    return updated_user


@user_router.post("/me/forgot-password")
async def forgot_my_password(
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(Security.get_required_user)
) -> str:
    await user_service.forgot_my_password(current_user.email)
    return f"Message with code is sent to your email address: {current_user.email}"


@user_router.patch("/me/forgot-password/check")
async def forgot_my_password_check(
    user_data: CheckForgotPassword = Depends(),
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(Security.get_required_user)
) -> str:
    return await user_service.forgot_my_password_check(user_data, current_user)


@user_router.patch("/me/forgot-password/final")
async def forgot_my_password_final(
    user_data: UpdateForgotPassword,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(Security.get_required_user)
) -> UserRead:
    return await user_service.forgot_my_password_final(response, user_data, current_user, session)


@user_router.post("/me/update-password")
async def update_password(
    passwords: UpdatePassword,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(Security.get_required_user)
) -> str:
    await user_service.update_password(session, response, passwords, current_user)
    return "Password is successfully changed"
