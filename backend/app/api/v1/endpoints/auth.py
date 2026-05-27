"""
Endpoints de autenticación (E01) — Sprint 1.
R-0101 register/verify-email, R-0102 login,
R-0103 refresh, R-0104 logout, R-0105 forgot/reset password.
Rate limiting desactivado en TESTING=True (conftest lo setea).
"""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps.auth import DB, CurrentUser, RefreshTokenCookie
from app.core.config import settings
from app.core.exceptions import AppBaseError
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserRegisterRequest, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

# Rate limiting desactivado cuando TESTING=True
limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.RATE_LIMIT_ENABLED and not settings.TESTING,
)

COOKIE_MAX_AGE = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key="refresh_token", path="/")


@router.post("/register", response_model=MessageResponse, status_code=201)
@limiter.limit("5/15minutes")
async def register(request: Request, body: UserRegisterRequest, db: DB):
    """
    Registra un nuevo usuario.
    Primer usuario (COUNT=0) → rol admin (AG-01).
    Timezone detectada automáticamente por el frontend (AG-02).
    """
    service = AuthService(db)
    ip = request.client.host if request.client else None
    await service.register(body, ip=ip)
    return MessageResponse(
        message="Registro exitoso. Revisa tu email para verificar tu cuenta."
    )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(body: VerifyEmailRequest, db: DB):
    """Verifica el email con código de 6 dígitos. Máximo 5 intentos."""
    service = AuthService(db)
    await service.verify_email(body.email, body.code)
    return MessageResponse(message="Email verificado. Ya puedes iniciar sesión.")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(body: ResendVerificationRequest, db: DB):
    """Reenvía el código. Siempre responde 200."""
    service = AuthService(db)
    await service.resend_verification(body.email)
    return MessageResponse(
        message="Si el email está pendiente de verificación, recibirás un nuevo código."
    )


@router.post("/login")
@limiter.limit("5/15minutes")
async def login(request: Request, body: LoginRequest, db: DB):
    """
    Login exitoso → access token en body + refresh token en cookie HttpOnly.
    ADR-01: refresh token sin rotación en MVP.
    """
    service = AuthService(db)
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    access_token, raw_refresh = await service.login(
        body.email, body.password, user_agent=user_agent, ip=ip
    )

    from app.repositories.user_repository import UserRepository

    user = await UserRepository(db).get_by_email(body.email)

    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user).model_dump(mode="json"),
    }

    response = JSONResponse(content=response_data)
    _set_refresh_cookie(response, raw_refresh)
    return response


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(raw_refresh: RefreshTokenCookie, db: DB):
    """
    Silent refresh — nuevo access token desde cookie.
    ADR-01: no rota el refresh token.
    """
    service = AuthService(db)
    access_token, _ = await service.refresh_access_token(raw_refresh)
    return RefreshResponse(access_token=access_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    raw_refresh: RefreshTokenCookie,
    current_user: CurrentUser,
    db: DB,
):
    """Revoca el refresh token de esta sesión y limpia la cookie."""
    service = AuthService(db)
    ip = request.client.host if request.client else None
    await service.logout(raw_refresh, current_user.id, ip=ip)

    response = JSONResponse(content={"message": "Sesión cerrada correctamente."})
    _clear_refresh_cookie(response)
    return response


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/15minutes")
async def forgot_password(request: Request, body: ForgotPasswordRequest, db: DB):
    """
    Siempre responde 200 — no revela si el email existe (R-0105).
    Rate limit: 3 req / IP / 15 min.
    """
    service = AuthService(db)
    await service.forgot_password(body.email)
    return MessageResponse(
        message="Si el email está registrado, recibirás un enlace para restablecer tu contraseña."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, db: DB):
    """
    Restablece la contraseña. Token de un solo uso, expira en 1h.
    Revoca TODOS los refresh tokens del usuario (R-0105).
    """
    if len(body.new_password) < 8 or not any(c.isdigit() for c in body.new_password):
        raise AppBaseError(
            "INVALID_PASSWORD",
            "La contraseña debe tener al menos 8 caracteres y un número",
            422,
        )

    service = AuthService(db)
    await service.reset_password(body.token, body.new_password)

    response = JSONResponse(
        content={"message": "Contraseña restablecida. Ya puedes iniciar sesión."}
    )
    _clear_refresh_cookie(response)
    return response
