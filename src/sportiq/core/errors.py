from typing import Literal

from pydantic import BaseModel

ErrorCode = Literal[
    "ALL_SOURCES_FAILED",
    "RATE_LIMITED",
    "INVALID_INPUT",
    "UPSTREAM_TIMEOUT",
    "NOT_FOUND",
]


class AttemptRecord(BaseModel):
    name: str
    error: str


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str
    sources_tried: list[AttemptRecord] = []
    retry_after_seconds: int | None = None
    suggestion: str | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class SportiqError(Exception):
    code: ErrorCode = "ALL_SOURCES_FAILED"

    def __init__(self, message: str, attempts: list[dict] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.attempts = attempts or []


class AllSourcesFailedError(SportiqError):
    code: ErrorCode = "ALL_SOURCES_FAILED"


class RateLimitedError(SportiqError):
    code: ErrorCode = "RATE_LIMITED"


class UpstreamTimeoutError(SportiqError):
    code: ErrorCode = "UPSTREAM_TIMEOUT"


class NotFoundError(SportiqError):
    code: ErrorCode = "NOT_FOUND"


class InvalidInputError(SportiqError):
    code: ErrorCode = "INVALID_INPUT"


class MissingCredentialsError(SportiqError):
    """Raised by an adapter when required env credentials are absent.

    The chain treats this exactly like any other adapter failure and walks past
    it. Code is ALL_SOURCES_FAILED so the error envelope stays consistent.
    """

    code: ErrorCode = "ALL_SOURCES_FAILED"
