"""User-facing exception classes and error handling utilities.

This module provides a structured approach to error handling that separates
internal technical errors from user-facing messages, preventing information
leakage while providing helpful feedback to users.
"""

import logging
from typing import Any, Dict, Optional, Union

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class UserFacingError(Exception):
    """Base class for user-facing errors with safe error messages."""

    def __init__(
        self,
        user_message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.user_message = user_message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(user_message)


class ValidationError(UserFacingError):
    """User input validation errors."""

    def __init__(self, user_message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            user_message=user_message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class APIKeyError(UserFacingError):
    """API key related errors."""

    def __init__(
        self,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = (
            user_message
            or "API key required. Please provide a valid API key in the request headers."
        )
        super().__init__(
            user_message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="API_KEY_ERROR",
            details=details,
        )


class RateLimitError(UserFacingError):
    """Rate limiting errors."""

    def __init__(
        self,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = (
            user_message
            or "Request rate limit exceeded. Please wait before trying again."
        )
        super().__init__(
            user_message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_ERROR",
            details=details,
        )


class ContentNotFoundError(UserFacingError):
    """Content or resource not found errors."""

    def __init__(
        self,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = user_message or "The requested content could not be found."
        super().__init__(
            user_message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="CONTENT_NOT_FOUND",
            details=details,
        )


class ProcessingError(UserFacingError):
    """Content processing errors."""

    def __init__(
        self,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = (
            user_message
            or "Unable to process the content. Please try again or contact support if the issue persists."
        )
        super().__init__(
            user_message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="PROCESSING_ERROR",
            details=details,
        )


class AIServiceError(UserFacingError):
    """AI service related errors."""

    def __init__(
        self,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = (
            user_message
            or "The AI service is temporarily unavailable. Please try again in a few minutes."
        )
        super().__init__(
            user_message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="AI_SERVICE_ERROR",
            details=details,
        )


class ErrorSanitizer:
    """Utility class to sanitize and categorize exceptions into user-facing errors.

    This class prevents information leakage by:
    1. Categorizing technical exceptions into user-friendly error types
    2. Filtering out sensitive information (API keys, internal paths, etc.)
    3. Providing consistent error messages across the application
    """

    # Sensitive patterns that should never be exposed to users
    SENSITIVE_PATTERNS = [
        r"key[_-]?\w*[=:]\s*[\w\-]{10,}",  # API keys
        r"token[_-]?\w*[=:]\s*[\w\-]{10,}",  # Tokens
        r"secret[_-]?\w*[=:]\s*[\w\-]{10,}",  # Secrets
        r"proj_[a-zA-Z0-9]{20,}",  # Project IDs
        r"/[a-zA-Z0-9_\-/]+\.py",  # File paths
        r"line \d+",  # Line numbers
        r"Traceback \(most recent call last\)",  # Stack traces
        r'File "[^"]*"',  # File references
    ]

    @classmethod
    def sanitize_exception(cls, exception: Exception) -> UserFacingError:
        """Convert any exception into a safe, user-facing error.

        Args:
            exception: The original exception to sanitize

        Returns:
            UserFacingError: A safe, user-facing error with appropriate message
        """
        error_str = str(exception).lower()
        exception_type = type(exception).__name__

        # If it's already a user-facing error, return as-is
        if isinstance(exception, UserFacingError):
            return exception

        # Check for API key/authentication issues
        if cls._is_auth_error(error_str, exception_type):
            return cls._create_auth_error(error_str)

        # Check for rate limiting issues
        if cls._is_rate_limit_error(error_str):
            return RateLimitError()

        # Check for content not found
        if cls._is_not_found_error(error_str, exception_type):
            return cls._create_not_found_error()

        # Check for validation errors
        if cls._is_validation_error(error_str, exception_type):
            return cls._create_validation_error(error_str)

        # Check for AI service errors
        if cls._is_ai_service_error(error_str):
            return AIServiceError()

        # Check for processing errors
        if cls._is_processing_error(error_str, exception_type):
            return ProcessingError()

        # For any other error, return a generic processing error
        # This ensures no sensitive information leaks
        logger.error(f"Uncategorized exception: {exception_type}: {exception}")
        return ProcessingError("An unexpected error occurred. Please try again.")

    @classmethod
    def _is_auth_error(cls, error_str: str, exception_type: str) -> bool:
        """Check if error is authentication/authorization related."""
        auth_indicators = [
            "unauthorized",
            "authentication",
            "api key",
            "invalid key",
            "access denied",
            "permission denied",
            "401",
            "403",
            "does not have access",
            "authentication failed",
        ]
        return any(indicator in error_str for indicator in auth_indicators)

    @classmethod
    def _create_auth_error(cls, error_str: str) -> Union[APIKeyError, RateLimitError]:
        """Create appropriate auth error based on error content."""
        if "invalid" in error_str or "unauthorized" in error_str:
            return APIKeyError(
                "Invalid API key provided. Please check your API key and try again."
            )
        elif "access" in error_str and "model" in error_str:
            return APIKeyError(
                "Your API key does not have access to the requested model. Please check your subscription or try a different model."
            )
        elif "quota" in error_str or "limit" in error_str:
            return RateLimitError(
                "API quota or rate limit exceeded. Please wait before trying again."
            )
        else:
            return APIKeyError()

    @classmethod
    def _is_rate_limit_error(cls, error_str: str) -> bool:
        """Check if error is rate limiting related."""
        rate_indicators = ["rate limit", "quota", "too many requests", "429"]
        return any(indicator in error_str for indicator in rate_indicators)

    @classmethod
    def _is_not_found_error(cls, error_str: str, exception_type: str) -> bool:
        """Check if error is content not found related."""
        not_found_indicators = [
            "not found",
            "404",
            "does not exist",
            "missing",
            "filenotfounderror",
            "objectdoesnotexist",
        ]
        return any(
            indicator in error_str for indicator in not_found_indicators
        ) or exception_type in ["FileNotFoundError", "ObjectDoesNotExist", "Http404"]

    @classmethod
    def _create_not_found_error(cls) -> ContentNotFoundError:
        """Create content not found error."""
        return ContentNotFoundError(
            "The requested article or section could not be found. Please check the article title and section title."
        )

    @classmethod
    def _is_validation_error(cls, error_str: str, exception_type: str) -> bool:
        """Check if error is validation related."""
        validation_indicators = [
            "validation",
            "invalid input",
            "required field",
            "missing",
            "valueerror",
            "keyerror",
        ]
        return any(
            indicator in error_str for indicator in validation_indicators
        ) or exception_type in ["ValueError", "KeyError", "ValidationError"]

    @classmethod
    def _create_validation_error(cls, error_str: str) -> ValidationError:
        """Create validation error with safe message."""
        if "required" in error_str:
            return ValidationError(
                "Required information is missing. Please check your input and try again."
            )
        elif "invalid" in error_str:
            return ValidationError(
                "Invalid input provided. Please check your data and try again."
            )
        else:
            return ValidationError(
                "Input validation failed. Please check your data and try again."
            )

    @classmethod
    def _is_ai_service_error(cls, error_str: str) -> bool:
        """Check if error is AI service related."""
        ai_indicators = [
            "openai",
            "anthropic",
            "google",
            "gemini",
            "gpt",
            "claude",
            "model",
            "llm",
            "ai service",
            "timeout",
            "service unavailable",
        ]
        return any(indicator in error_str for indicator in ai_indicators)

    @classmethod
    def _is_processing_error(cls, error_str: str, exception_type: str) -> bool:
        """Check if error is content processing related."""
        processing_indicators = [
            "processing",
            "parsing",
            "format",
            "encoding",
            "decode",
            "memory",
            "timeout",
        ]
        return any(
            indicator in error_str for indicator in processing_indicators
        ) or exception_type in ["MemoryError", "TimeoutError", "UnicodeError"]


def custom_exception_handler(exc, context):
    """Custom exception handler for Django REST Framework.

    This handler ensures that all exceptions are properly sanitized
    before being returned to users, preventing information leakage.
    """
    # First, let DRF handle the exception if it can
    response = drf_exception_handler(exc, context)

    if response is not None:
        # DRF handled it, but we still need to sanitize
        if isinstance(exc, UserFacingError):
            # Already safe, just format consistently
            custom_response_data: Dict[str, Any] = {
                "error": exc.user_message,
                "error_code": exc.error_code,
            }
            if exc.details:
                custom_response_data["details"] = exc.details
            response.data = custom_response_data
        else:
            # Sanitize DRF's default error response
            sanitized_error = ErrorSanitizer.sanitize_exception(exc)
            response.data = {
                "error": sanitized_error.user_message,
                "error_code": sanitized_error.error_code,
            }
            response.status_code = sanitized_error.status_code
    else:
        # DRF didn't handle it, so we need to create a response
        sanitized_error = ErrorSanitizer.sanitize_exception(exc)

        # Log the original exception for debugging
        logger.error(
            f"Unhandled exception in {context.get('view', 'unknown view')}: "
            f"{type(exc).__name__}: {exc}",
            exc_info=True,
        )

        response = Response(
            {
                "error": sanitized_error.user_message,
                "error_code": sanitized_error.error_code,
            },
            status=sanitized_error.status_code,
        )

    return response
