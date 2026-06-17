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


# structlog level -> Cloud Logging severity. Cloud Logging keys severity-based
# filtering, alerting and Error Reporting off the `severity` field, not the
# `level` field `add_log_level` emits — so a failed tool logged at `error` is
# invisible to Error Reporting until we map it across.
_GCP_SEVERITY = {
    "critical": "CRITICAL",
    "exception": "ERROR",
    "error": "ERROR",
    "warning": "WARNING",
    "warn": "WARNING",
    "info": "INFO",
    "debug": "DEBUG",
    "notset": "DEFAULT",
}


def _gcp_severity_processor(logger: object, method: str, event_dict: dict) -> dict:
    """Mirror structlog's `level` into Cloud Logging's `severity` field."""
    level = event_dict.get("level")
    if level:
        event_dict["severity"] = _GCP_SEVERITY.get(level, level.upper())
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
        # GCP-only: add `severity` so Cloud Logging/Error Reporting see error
        # levels. Skipped for the pretty dev renderer (would be console noise).
        processors.append(_gcp_severity_processor)
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
