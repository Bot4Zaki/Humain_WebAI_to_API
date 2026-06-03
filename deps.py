"""
Shared singletons – BrowserManager and rate limiter.

This module is deliberately kept **dependency-free** (no FastAPI imports here)
to avoid circular import issues. Both ``app.main`` and ``app.routes`` import
from this file.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.browser import BrowserManager

# Playwright browser singleton – started in app.main startup hook
browser_manager = BrowserManager()

# Rate limiter – attached to FastAPI app state in app.main
limiter = Limiter(key_func=get_remote_address, default_limits=[])
