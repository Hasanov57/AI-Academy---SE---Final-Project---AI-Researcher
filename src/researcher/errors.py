"""Domain-specific failures shown as clean CLI messages."""


class ResearcherError(RuntimeError):
    """Base class for expected application failures."""


class ConfigurationError(ResearcherError):
    """Raised when environment configuration is incomplete or invalid."""


class StorageError(ResearcherError):
    """Raised when persistent storage cannot complete an operation."""


class NoSourcesError(ResearcherError):
    """Raised when every selected upstream source fails or returns no data."""


class CitationValidationError(ResearcherError):
    """Raised when a synthesized answer contains unsafe citation markers."""
