"""
Excepciones de dominio del proyecto.
El handler global en main.py las convierte al formato { error: { code, message } }.
"""


class AppBaseError(Exception):
    """Base para excepciones de dominio."""

    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ── Auth ───────────────────────────────────────────────────────────────────────


class InvalidCredentialsError(AppBaseError):
    def __init__(self):
        super().__init__("INVALID_CREDENTIALS", "Credenciales incorrectas", 401)


class EmailNotVerifiedError(AppBaseError):
    def __init__(self):
        super().__init__(
            "EMAIL_NOT_VERIFIED",
            "Debes verificar tu email antes de iniciar sesión",
            403,
        )


class TokenExpiredError(AppBaseError):
    def __init__(self):
        super().__init__("TOKEN_EXPIRED", "El token ha expirado", 401)


class TokenInvalidError(AppBaseError):
    def __init__(self):
        super().__init__("TOKEN_INVALID", "Token inválido", 401)


class TokenRevokedError(AppBaseError):
    def __init__(self):
        super().__init__("TOKEN_REVOKED", "Token revocado", 401)


class MaxVerificationAttemptsError(AppBaseError):
    def __init__(self):
        super().__init__(
            "MAX_VERIFICATION_ATTEMPTS",
            "Demasiados intentos. Solicita un nuevo código",
            429,
        )


# ── Users ──────────────────────────────────────────────────────────────────────


class EmailAlreadyExistsError(AppBaseError):
    def __init__(self):
        super().__init__("EMAIL_ALREADY_EXISTS", "El email ya está registrado", 409)


class UsernameAlreadyExistsError(AppBaseError):
    def __init__(self):
        super().__init__("USERNAME_ALREADY_EXISTS", "El username ya está en uso", 409)


class UserNotFoundError(AppBaseError):
    def __init__(self):
        super().__init__("USER_NOT_FOUND", "Usuario no encontrado", 404)


class InvalidTimezoneError(AppBaseError):
    def __init__(self, tz: str):
        super().__init__("INVALID_TIMEZONE", f"Timezone inválida: {tz}", 422)


class InsufficientPermissionsError(AppBaseError):
    def __init__(self):
        super().__init__(
            "INSUFFICIENT_PERMISSIONS",
            "No tienes permisos para realizar esta acción",
            403,
        )
