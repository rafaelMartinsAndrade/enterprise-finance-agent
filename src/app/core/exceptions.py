class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        details: dict | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentication failed.") -> None:
        super().__init__(message, code="authentication_error", status_code=401)


class DomainValidationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="domain_validation_error", status_code=400)


class NotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="not_found", status_code=404)


class ProviderUnavailableError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="provider_unavailable", status_code=503)


class ProviderTimeoutError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="provider_timeout", status_code=504)


class ProcessingError(AppError):
    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message, code="processing_error", status_code=500, details=details)


class RetryableToolError(AppError):
    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message, code="retryable_tool_error", status_code=503, details=details)
