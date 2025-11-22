from datetime import datetime
from typing import Optional
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette_admin.auth import AdminUser, AuthProvider
from starlette_admin.exceptions import LoginFailed
import jwt as pyjwt
from api.src.core.config import Configuration
from api.src.core.security import Security
from api.src.database.database import get_async_session
from api.src.dependencies.repositories import get_staff_repository
from api.src.repositories.staff.base import BaseStaffRepository


class AdminAuth(AuthProvider):
    login_path = "/login"
    logout_path = "/logout"

    def __init__(self, staff_repository: BaseStaffRepository):
        self.staff_repository = staff_repository
        super().__init__()

    async def login(
            self,
            username: str,
            password: str,
            remember_me: bool,
            request: Request,
            response: Response
    ) -> Response:
        async for session in get_async_session():
            user = await self.staff_repository.find_by_login(session, username)
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
                user = await self.staff_repository.find_by_login(session, payload.get("sub"))
                return bool(user)
        except Exception:
            return False

    def get_admin_user(self, request: Request) -> Optional[AdminUser]:
        token = request.session.get("fooddiary_staff_access_token")
        if token:
            try:
                payload = pyjwt.decode(
                    token,
                    Configuration.STAFF_SECRET_AUTH,
                    algorithms=[Configuration.ALGORITHM]
                )
                username = payload.get("sub")
                if username:
                    return AdminUser(username=username)
            except Exception:
                pass
        return AdminUser(username="admin")

    async def logout(self, request: Request) -> Response:
        request.session.clear()
        return RedirectResponse(request.url_for("admin:login"), status_code=302)


admin_auth = AdminAuth(get_staff_repository())
