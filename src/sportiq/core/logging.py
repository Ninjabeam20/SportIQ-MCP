import logging
import sys

import structlog

from sportiq.config import settings


def _redact_event_processor(logger: object, method: str, event_dict: dict) -> dict:
    """Scrub secret values from all string fields in a structlog event dict."""
    from sportiq.core.redact import scrub

    for key in list(event_dict.keys()):
        val = event_dict[key]
        if isinstance(val, str):
            event_dict[key] = scrub(val)
    return event_dict


def configure_logging() -> None:
    """Configure structlog. Pretty in dev (default), JSON in prod."""
    level = getattr(logging, settings.sportiq_log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stderr, level=level)

    processors: list = [
        _redact_event_processor,
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    if settings.sportiq_log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
