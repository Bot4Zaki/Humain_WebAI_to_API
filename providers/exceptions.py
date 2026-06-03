"""
Custom exceptions for provider interactions.
"""


class ProviderError(Exception):
    """Raised when a provider interaction fails (DOM, timeout, auth, etc.)."""
    pass


class AuthenticationError(ProviderError):
    """Raised when the user is not logged into the provider."""
    pass


class SelectorError(ProviderError):
    """Raised when an expected DOM element cannot be found."""
    pass


class ResponseTimeoutError(ProviderError):
    """Raised when the provider takes too long to respond."""
    pass
