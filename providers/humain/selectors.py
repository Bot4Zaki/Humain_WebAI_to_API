"""
HUMAIN-specific DOM selectors.

Updated after live DOM inspection: HUMAIN currently uses placeholder
attributes instead of data-testid.

Usage:
    Use ``get_first_matching(page, SELECTORS.message_input)`` to find the
    first working selector from a list of candidates.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Chat input ──────────────────────────────────────────────────────────
# Ordered fallback list – tried in order until one matches.
# Based on live DOM inspection: placeholders are used.
MESSAGE_INPUT_SELECTORS = [
    'textarea[placeholder="Ask me anything..."]',
    'textarea[placeholder="Write your thoughts..."]',
    'textarea',
    '[contenteditable="true"]',
    'div[role="textbox"]',
]

# ── Send button ─────────────────────────────────────────────────────────
SEND_BUTTON_SELECTORS = [
    'button[type="submit"]',
    'button:has(svg)',
    'button:has-text("Send")',
    'button:last-of-type',
]

# ── Response text ───────────────────────────────────────────────────────
RESPONSE_TEXT_SELECTORS = [
    '.prose',
    '[class*="message"]',
    '[class*="response"]',
    'div[class*="markdown"]',
    '[class*="assistant"]',
    '[class*="chat"] [class*="bubble"]',
    'article',
    'main',
    '#__next',
    'body',
]

# ── Typing indicator ──────────────────────────────────────────────────
TYPING_INDICATOR_SELECTORS = [
    '[class*="typing"]',
    '[class*="spinner"]',
    '[class*="loading"]',
]

# ── Logged-in indicator ────────────────────────────────────────────────
LOGGED_IN_SELECTORS = [
    '[class*="sidebar"]',
    'nav',
    'button[class*="user"]',
]

# ── Login button ────────────────────────────────────────────────────────
LOGIN_BUTTON_SELECTORS = [
    'button:has-text("Log in")',
    'a:has-text("Log in")',
    'button:has-text("Sign in")',
    'button:has-text("Login")',
]

# ── Overlay / modal dismissers ───────────────────────────────────────────
# High z-index overlays that intercept pointer events before the chat input.
OVERLAY_DISMISS_SELECTORS = [
    'div.fixed.inset-0',
    '[class*="z-[9999"]',
    '[class*="z-[99999"]',
    '[class*="z-[999999"]',
    '[class*="modal"][class*="fixed"]',
    '[class*="dialog"][class*="fixed"]',
]


@dataclass(frozen=True)
class PageSelectors:
    """Selectors for the HUMAIN chat interface.

    Each field is either a single string (legacy) or a list of strings
    (fallback).  Provider code should use ``get_first_matching()`` to
    resolve lists at runtime.
    """

    # ── Authentication ────────────────────────────────────────────
    logged_in_indicator: list = field(default_factory=lambda: LOGGED_IN_SELECTORS)
    login_button: list = field(default_factory=lambda: LOGIN_BUTTON_SELECTORS)

    # ── Chat input ──────────────────────────────────────────────
    message_input: list = field(default_factory=lambda: MESSAGE_INPUT_SELECTORS)
    send_button: list = field(default_factory=lambda: SEND_BUTTON_SELECTORS)

    # ── Response ──────────────────────────────────────────────────
    response_container: str = '[class*="message"]'
    response_text_block: list = field(default_factory=lambda: RESPONSE_TEXT_SELECTORS)

    # ── Status indicators ───────────────────────────────────────
    typing_indicator: list = field(default_factory=lambda: TYPING_INDICATOR_SELECTORS)

    # ── Overlay dismissers ─────────────────────────────────────────
    overlay_dismiss: list = field(default_factory=lambda: OVERLAY_DISMISS_SELECTORS)

    # ── Conversation management ─────────────────────────────────
    new_chat_button: str = 'button:has-text("New chat")'


# Singleton instance for easy import.
selectors = PageSelectors()
