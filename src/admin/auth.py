from datetime import datetime
from typing import Optional, AsyncGenerator

from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette_admin.auth import AdminUser, AuthProvider
from starlette_admin.exceptions import FormValidationError, LoginFailed
import jwt as pyjwt
from src.core.config import Configuration
from src.core.security import Security
from src.daos.staff_dao import StaffDAO
from src.database.database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession


class AdminAuth(AuthProvider):
    async def login(
            self,
            username: str,
            password: str,
            remember_me: bool,
            request: Request,
            response: Response
    ) -> Response:
        async for session in get_async_session():
            user = await StaffDAO.find_by_login(session, username)
            if not user or not Security.verify_password(password, user.hashed_password):
                raise LoginFailed("Invalid username or password")

            access_token = Security.create_access_token(
                data={"sub": user.login},
                secret_key=Configuration.STAFF_SECRET_AUTH
            )

            request.session.update({"fooddiary_staff_access_token": access_token})
            return response

    async def is_authenticated(self, request: Request) -> bool:
        token = request.session.get("fooddiary_staff_access_token")
        if not token:
            return False

        try:
            payload = pyjwt.decode(
                token,
                Configuration.STAFF_SECRET_AUTH,
                algorithms=[Configuration.ALGORITHM]
            )
            if int(payload.get("exp", 0)) < datetime.utcnow().timestamp():
                return False

            async for session in get_async_session():
                user = await StaffDAO.find_one_or_none(session, login=payload.get("sub"))
                return bool(user)
        except Exception:
            return False

    def get_admin_user(self, request: Request) -> Optional[AdminUser]:
        return AdminUser(username="admin")

    async def logout(self, request: Request) -> Response:
        request.session.clear()
        return RedirectResponse(request.url_for("admin:login"), status_code=302)


admin_auth = AdminAuth()
