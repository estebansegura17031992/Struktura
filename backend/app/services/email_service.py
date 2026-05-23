"""
Servicio de email — Resend en producción, consola en desarrollo.
EMAIL_DEV_MODE=true imprime el email en consola sin consumir cuota Resend (R-0101).
"""
from app.core.config import settings
from app.core.logging import get_logger
 
logger = get_logger(__name__)
 
 
async def send_verification_email(email: str, username: str, code: str) -> None:
    subject = f"[{settings.APP_NAME}] Verifica tu email — código: {code}"
    html = f"""
    <h2>Hola {username},</h2>
    <p>Tu código de verificación es:</p>
    <h1 style="letter-spacing:8px;font-size:48px">{code}</h1>
    <p>Válido por <strong>24 horas</strong>. Máximo 5 intentos.</p>
    <p>Si no creaste esta cuenta, ignora este mensaje.</p>
    """
    await _send(to=email, subject=subject, html=html)
 
 
async def send_reset_password_email(email: str, username: str, reset_url: str) -> None:
    subject = f"[{settings.APP_NAME}] Recupera tu contraseña"
    html = f"""
    <h2>Hola {username},</h2>
    <p>Recibimos una solicitud para restablecer tu contraseña.</p>
    <p><a href="{reset_url}" style="padding:10px 20px;background:#7c6af7;color:#fff;
       border-radius:6px;text-decoration:none">Restablecer contraseña</a></p>
    <p>Este enlace expira en <strong>1 hora</strong> y es de un solo uso.</p>
    <p>Si no solicitaste esto, ignora este mensaje — tu contraseña no cambiará.</p>
    """
    await _send(to=email, subject=subject, html=html)
 
 
async def _send(to: str, subject: str, html: str) -> None:
    if settings.EMAIL_DEV_MODE:
        # Imprime en consola — no consume cuota Resend en desarrollo
        logger.info(
            "email_dev_mode",
            to=to,
            subject=subject,
            body_preview=html[:120].replace("\n", " "),
        )
        return
 
    try:
        import resend
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        logger.info("email_sent", to=to, subject=subject)
    except Exception as e:
        # No bloquear el flujo principal si el email falla
        logger.error("email_send_failed", to=to, error=str(e))
