"""
Logging estructurado con structlog (R-0803).
Emite JSON a stdout. Railway lo captura automáticamente.
Nunca incluir datos sensibles (contraseñas, tokens, hashes).
"""
import logging
import sys
 
import structlog
 
 
def configure_logging(debug: bool = False) -> None:
    log_level = logging.DEBUG if debug else logging.INFO
 
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
 
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            # add_logger_name removido — incompatible con PrintLogger
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
 
 
def get_logger(name: str = __name__):
    return structlog.get_logger(name)
