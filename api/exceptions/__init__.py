"""API exceptions module.

Provides user-facing exception classes and error handling utilities.
"""

from api.exceptions.user_facing_exceptions import (
    AIServiceError,
    APIKeyError,
    ContentNotFoundError,
    ErrorSanitizer,
    ProcessingError,
    RateLimitError,
    UserFacingError,
    ValidationError,
    custom_exception_handler,
)

__all__ = [
    "UserFacingError",
    "ValidationError",
    "APIKeyError",
    "RateLimitError",
    "ContentNotFoundError",
    "ProcessingError",
    "AIServiceError",
    "ErrorSanitizer",
    "custom_exception_handler",
]
