class UniProtAPIError(Exception):
    """Raised when UniProt API responses indicate a persistent failure."""


class UniProtNotFoundError(UniProtAPIError):
    """Raised when a requested UniProt accession is not found."""


class RuleValidationError(ValueError):
    """Raised when YAML rule definitions are malformed."""
