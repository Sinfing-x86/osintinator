# core/exceptions.py
"""
OSINTINATOR - Custom Exceptions
Centralized exception hierarchy for better error handling, logging, and debugging.
"""

class OSINTinatorError(Exception):
    """Base exception for all OSINTINATOR errors."""
    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# ====================== Configuration & Initialization ======================
class ConfigurationError(OSINTinatorError):
    """Raised for configuration, environment, or settings issues."""
    pass


class ApiKeyMissingError(ConfigurationError):
    """Raised when a required third-party API key is not configured."""
    pass


# ====================== Ingestion & Target Handling ======================
class IngestionError(OSINTinatorError):
    """Raised during target ingestion, normalization, or validation."""
    pass


class InvalidTargetError(IngestionError):
    """Target data failed validation or normalization."""
    pass


class UnsupportedIdentifierError(IngestionError):
    """Raised for unsupported Indian or international identifiers."""
    pass


# ====================== Module & Execution Errors ======================
class ModuleExecutionError(OSINTinatorError):
    """Raised when a registered module (username, network, etc.) fails."""
    pass


class ModuleNotFoundError(OSINTinatorError):
    """Raised when attempting to run a module that is not registered."""
    pass


# ====================== Integration & API Errors ======================
class IntegrationError(OSINTinatorError):
    """Base class for third-party API / integration failures."""
    pass


class ApiRateLimitError(IntegrationError):
    """Raised when a third-party service rate limit is hit."""
    pass


class ApiAuthenticationError(IntegrationError):
    """Raised on API key rejection or authentication failure."""
    pass


class ApiResponseError(IntegrationError):
    """Raised when an API returns an error status or malformed response."""
    def __init__(self, message: str, status_code: int | None = None, response: dict | None = None):
        super().__init__(message, {"status_code": status_code, "response": response})
        self.status_code = status_code


# ====================== Privacy & Compliance ======================
class PrivacyViolationError(OSINTinatorError):
    """Raised when an operation would violate DPDP Act or strict_privacy_mode."""
    pass


class DataRetentionError(OSINTinatorError):
    """Raised when attempting to persist data beyond configured retention policy."""
    pass


# ====================== Reporting & Output ======================
class ReportGenerationError(OSINTinatorError):
    """Raised during final report generation or templating."""
    pass


class EvidenceHandlingError(OSINTinatorError):
    """Raised for issues with evidence storage, hashing, or chain of custody."""
    pass


# ====================== Workflow & Orchestration ======================
class WorkflowError(OSINTinatorError):
    """General workflow / coordinator level errors."""
    pass


class TaskTimeoutError(WorkflowError):
    """Raised when a task exceeds configured timeout."""
    pass


# ====================== Utility Functions ======================
def handle_exception(e: Exception, context: str | None = None) -> None:
    """Standardized logging helper for exceptions."""
    import logging
    logger = logging.getLogger(__name__)
    
    if isinstance(e, OSINTinatorError):
        logger.error(f"{context or 'OSINTINATOR'} Error: {e}")
    else:
        logger.exception(f"Unexpected error in {context or 'unknown context'}: {e}")


__all__ = [
    "OSINTinatorError",
    "ConfigurationError",
    "ApiKeyMissingError",
    "IngestionError",
    "InvalidTargetError",
    "UnsupportedIdentifierError",
    "ModuleExecutionError",
    "ModuleNotFoundError",
    "IntegrationError",
    "ApiRateLimitError",
    "ApiAuthenticationError",
    "ApiResponseError",
    "PrivacyViolationError",
    "DataRetentionError",
    "ReportGenerationError",
    "EvidenceHandlingError",
    "WorkflowError",
    "TaskTimeoutError",
    "handle_exception",
]