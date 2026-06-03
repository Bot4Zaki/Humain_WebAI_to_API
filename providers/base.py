"""
Abstract base for chat providers.

Every provider must implement the ``chat`` method which takes a list of
messages and returns the assistant reply as a plain string.

To add a new provider:
    1. Create providers/<name>/provider.py implementing BaseProvider.
    2. Add selectors to providers/<name>/selectors.py.
    3. Register the provider in the router or a provider registry.
"""

from __future__ import annotations

import abc

from app.schemas import ChatMessage


class BaseProvider(abc.ABC):
    """Interface that every chat provider must implement."""

    @abc.abstractmethod
    async def chat(self, messages: list[ChatMessage]) -> str:
        """
        Send *messages* to the provider and return the assistant reply.

        Parameters
        ----------
        messages:
            Conversation history in OpenAI format (role + content).

        Returns
        -------
        str
            The assistant's reply text.

        Raises
        ------
        ProviderError
            On any upstream / DOM interaction failure.
        """
        ...

    @abc.abstractmethod
    async def is_authenticated(self) -> bool:
        """Return True if the user appears to be logged in."""
        ...
