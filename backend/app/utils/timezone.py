"""
Validación de timezone IANA (AG-02).
tzdata debe estar instalado (ver requirements.txt) para que zoneinfo
tenga las zonas completas en Windows y Linux sin tzdata del SO.
"""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def validate_timezone(tz: str) -> str:
    """
    Valida que el string sea una timezone IANA válida.
    Usa ZoneInfo directamente — más robusto que available_timezones()
    que en Windows sin tzdata devuelve un set vacío.
    Raises InvalidTimezoneError si no es válida.
    """
    from app.core.exceptions import InvalidTimezoneError

    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, KeyError):
        raise InvalidTimezoneError(tz) from None
    return tz
