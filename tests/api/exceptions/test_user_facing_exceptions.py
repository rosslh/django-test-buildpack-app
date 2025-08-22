"""
Tests for user-facing exception handling and error sanitization.
"""

from unittest.mock import patch

from rest_framework import status
from rest_framework.response import Response

from api.exceptions import (
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


class TestUserFacingExceptions:
    """Test user-facing exception classes."""

    def test_user_facing_error_base(self):
        """Test the base UserFacingError class."""
        error = UserFacingError(
            user_message="Test error",
            status_code=400,
            error_code="TEST_ERROR",
            details={"field": "value"},
        )

        assert error.user_message == "Test error"
        assert error.status_code == 400
        assert error.error_code == "TEST_ERROR"
        assert error.details == {"field": "value"}

    def test_validation_error(self):
        """Test ValidationError defaults."""
        error = ValidationError("Invalid input")

        assert error.user_message == "Invalid input"
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.error_code == "VALIDATION_ERROR"

    def test_api_key_error(self):
        """Test APIKeyError defaults."""
        error = APIKeyError()

        assert "API key required" in error.user_message
        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.error_code == "API_KEY_ERROR"

    def test_api_key_error_custom_message(self):
        """Test APIKeyError with custom message."""
        error = APIKeyError("Custom API key message")

        assert error.user_message == "Custom API key message"
        assert error.status_code == status.HTTP_401_UNAUTHORIZED

    def test_rate_limit_error(self):
        """Test RateLimitError defaults."""
        error = RateLimitError()

        assert "rate limit exceeded" in error.user_message.lower()
        assert error.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert error.error_code == "RATE_LIMIT_ERROR"

    def test_content_not_found_error(self):
        """Test ContentNotFoundError defaults."""
        error = ContentNotFoundError()

        assert "could not be found" in error.user_message
        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.error_code == "CONTENT_NOT_FOUND"

    def test_processing_error(self):
        """Test ProcessingError defaults."""
        error = ProcessingError()

        assert "unable to process" in error.user_message.lower()
        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert error.error_code == "PROCESSING_ERROR"

    def test_ai_service_error(self):
        """Test AIServiceError defaults."""
        error = AIServiceError()

        assert "ai service" in error.user_message.lower()
        assert error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert error.error_code == "AI_SERVICE_ERROR"


class TestErrorSanitizer:
    """Test error sanitization functionality."""

    def test_sanitize_already_user_facing_error(self):
        """Test that user-facing errors are returned as-is."""
        original_error = ValidationError("Test validation error")
        sanitized = ErrorSanitizer.sanitize_exception(original_error)

        assert sanitized is original_error

    def test_sanitize_auth_error_invalid_key(self):
        """Test sanitization of authentication errors."""
        error = Exception("unauthorized: invalid api key")
        sanitized = ErrorSanitizer.sanitize_exception(error)

        assert isinstance(sanitized, APIKeyError)
        assert "invalid api key" in sanitized.user_message.lower()

    def test_sanitize_auth_error_no_access(self):
        """Test sanitization of access errors."""
        error = Exception("does not have access to model gpt-4")
        sanitized = ErrorSanitizer.sanitize_exception(error)

        assert isinstance(sanitized, APIKeyError)
        assert "does not have access" in sanitized.user_message

    def test_sanitize_rate_limit_error(self):
        """Test sanitization of rate limit errors."""
        error = Exception("rate limit exceeded")
        sanitized = ErrorSanitizer.sanitize_exception(error)

        assert isinstance(sanitized, RateLimitError)

    def test_sanitize_not_found_error(self):
        """Test sanitization of not found errors."""
        error = Exception("article not found")
        sanitized = ErrorSanitizer.sanitize_exception(error)

        assert isinstance(sanitized, ContentNotFoundError)

    def test_sanitize_validation_error(self):
        """Test sanitization of validation errors."""
        error = ValueError("invalid input provided")
        sanitized = ErrorSanitizer.sanitize_exception(error)

        assert isinstance(sanitized, ValidationError)

    def test_sanitize_ai_service_error(self):
        """Test sanitization of AI service errors."""
        error = Exception("openai api error occurred")
        sanitized = ErrorSanitizer.sanitize_exception(error)

        assert isinstance(sanitized, AIServiceError)

    def test_sanitize_processing_error(self):
        """Test sanitization of processing errors."""
        error = Exception("parsing failed")
        sanitized = ErrorSanitizer.sanitize_exception(error)

        assert isinstance(sanitized, ProcessingError)

    def test_sanitize_unknown_error(self):
        """Test sanitization of unknown errors."""
        error = Exception("some random unknown error")
        sanitized = ErrorSanitizer.sanitize_exception(error)

        assert isinstance(sanitized, ProcessingError)
        assert "unexpected error occurred" in sanitized.user_message.lower()

    def test_sanitize_sensitive_information_filtering(self):
        """Test that sensitive information is filtered out."""
        # This test ensures that even if an error message contains sensitive info,
        # it gets sanitized to a safe message
        error = Exception(
            "Error code: 403 - {'error': {'message': 'Project `proj_nQYmw72zQUWl42pw9oLQafWl` does not have access to model `gpt-4o-mini`'}}"
        )
        sanitized = ErrorSanitizer.sanitize_exception(error)

        assert isinstance(sanitized, APIKeyError)
        # Should not contain the original project ID
        assert "proj_nQYmw72zQUWl42pw9oLQafWl" not in sanitized.user_message
        # Should provide helpful message instead
        assert "access" in sanitized.user_message.lower()

    def test_sanitize_file_paths_removed(self):
        """Test that file paths are not exposed in error messages."""
        error = Exception(
            "Processing failed in '/path/to/sensitive/file.py' on line 123"
        )
        sanitized = ErrorSanitizer.sanitize_exception(error)

        assert isinstance(sanitized, ProcessingError)
        # Original paths and line numbers should not be in the message
        assert "/path/to/sensitive/file.py" not in sanitized.user_message
        assert "line 123" not in sanitized.user_message

    def test_sanitize_api_keys_removed(self):
        """Test that API keys are not exposed in error messages."""
        error = Exception("Authentication failed: api_key=sk-1234567890abcdef")
        sanitized = ErrorSanitizer.sanitize_exception(error)

        assert isinstance(sanitized, APIKeyError)
        # API key should not be in the message
        assert "sk-1234567890abcdef" not in sanitized.user_message

    def test_check_auth_error_patterns(self):
        """Test specific auth error pattern detection."""
        test_cases = [
            ("unauthorized access", True),
            ("authentication failed", True),
            ("invalid api key", True),
            ("403 forbidden", True),
            ("does not have access to model", True),
            ("random error message", False),
        ]

        for error_str, expected in test_cases:
            result = ErrorSanitizer._is_auth_error(error_str.lower(), "Exception")
            assert result == expected, f"Failed for: {error_str}"

    def test_check_rate_limit_patterns(self):
        """Test rate limit pattern detection."""
        test_cases = [
            ("rate limit exceeded", True),
            ("quota exceeded", True),
            ("too many requests", True),
            ("429 error", True),
            ("normal error", False),
        ]

        for error_str, expected in test_cases:
            result = ErrorSanitizer._is_rate_limit_error(error_str.lower())
            assert result == expected, f"Failed for: {error_str}"

    def test_check_ai_service_patterns(self):
        """Test AI service error pattern detection."""
        test_cases = [
            ("openai error", True),
            ("anthropic timeout", True),
            ("google gemini issue", True),
            ("gpt model error", True),
            ("claude api error", True),
            ("llm processing failed", True),
            ("database error", False),
        ]

        for error_str, expected in test_cases:
            result = ErrorSanitizer._is_ai_service_error(error_str.lower())
            assert result == expected, f"Failed for: {error_str}"

    def test_create_auth_error_quota_case(self):
        """Test _create_auth_error when quota is mentioned."""
        error = ErrorSanitizer._create_auth_error("quota exceeded for api key")
        assert isinstance(error, RateLimitError)
        assert "quota or rate limit" in error.user_message.lower()

    def test_create_validation_error_required_case(self):
        """Test _create_validation_error when required field is mentioned."""
        error = ErrorSanitizer._create_validation_error("required field missing")
        assert isinstance(error, ValidationError)
        assert "required information" in error.user_message.lower()

    def test_create_validation_error_generic_case(self):
        """Test _create_validation_error for generic validation errors."""
        error = ErrorSanitizer._create_validation_error("some validation problem")
        assert isinstance(error, ValidationError)
        assert "input validation failed" in error.user_message.lower()


class TestCustomExceptionHandler:
    """Test the custom exception handler for DRF."""

    def test_handler_with_user_facing_error(self):
        """Test handler when exception is already UserFacingError."""
        exc = ValidationError("Test validation error", details={"field": "test"})
        context = {"view": "test_view"}

        # Mock DRF handler to return a response
        with patch(
            "api.exceptions.user_facing_exceptions.drf_exception_handler"
        ) as mock_drf:
            mock_response = Response({"error": "test"}, status=400)
            mock_drf.return_value = mock_response

            response = custom_exception_handler(exc, context)

            assert response.data == {
                "error": "Test validation error",
                "error_code": "VALIDATION_ERROR",
                "details": {"field": "test"},
            }
            assert response.status_code == 400

    def test_handler_with_non_user_facing_error(self):
        """Test handler when exception needs sanitization."""
        exc = ValueError("Sensitive error with /path/to/file")
        context = {"view": "test_view"}

        # Mock DRF handler to return a response
        with patch(
            "api.exceptions.user_facing_exceptions.drf_exception_handler"
        ) as mock_drf:
            mock_response = Response({"detail": "error"}, status=400)
            mock_drf.return_value = mock_response

            response = custom_exception_handler(exc, context)

            assert response.data["error_code"] == "VALIDATION_ERROR"
            assert "/path/to/file" not in response.data["error"]

    def test_handler_when_drf_returns_none(self):
        """Test handler when DRF doesn't handle the exception."""
        exc = Exception("Unhandled error")
        context = {"view": "test_view"}

        # Mock DRF handler to return None (doesn't handle it)
        with patch(
            "api.exceptions.user_facing_exceptions.drf_exception_handler"
        ) as mock_drf:
            mock_drf.return_value = None

            with patch("api.exceptions.user_facing_exceptions.logger") as mock_logger:
                response = custom_exception_handler(exc, context)

                # Should log the error (called twice - once in ErrorSanitizer, once in handler)
                assert mock_logger.error.call_count == 2

                # Check the second call is from custom_exception_handler
                second_call = mock_logger.error.call_args_list[1]
                assert "Unhandled exception in test_view" in str(second_call)

                # Should return sanitized response
                assert response.status_code == 422  # ProcessingError default
                assert response.data["error_code"] == "PROCESSING_ERROR"
                assert "unexpected error" in response.data["error"].lower()

    def test_handler_preserves_user_facing_error_without_details(self):
        """Test handler with UserFacingError that has no details."""
        exc = APIKeyError("Custom API key error")
        context = {"view": "test_view"}

        with patch(
            "api.exceptions.user_facing_exceptions.drf_exception_handler"
        ) as mock_drf:
            mock_response = Response({"error": "test"}, status=401)
            mock_drf.return_value = mock_response

            response = custom_exception_handler(exc, context)

            # Should not have details key if no details provided
            assert response.data == {
                "error": "Custom API key error",
                "error_code": "API_KEY_ERROR",
            }
            assert "details" not in response.data
