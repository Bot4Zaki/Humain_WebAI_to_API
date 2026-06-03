from typing import Optional
"""
Singleton Playwright browser manager.

Owns the playwright instance, the persistent browser context, and the page
used to interact with HUMAIN Chat. Only one page is kept open to preserve
session state across requests.
"""

import logging
from pathlib import Path

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from app.config import settings

logger = logging.getLogger("humain-webai-to-api.browser")


class BrowserManager:
    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    # ── Lifecycle ───────────────────────────────────────────────────

    async def start(self) -> None:
        """Launch Playwright with a persistent Chromium profile."""
        profile = Path(settings.browser_profile_dir).resolve()
        profile.mkdir(parents=True, exist_ok=True)

        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            str(profile),
            headless=False,  # keep visible for manual login
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        self._page = await self._get_or_create_page()
        await self._page.goto(settings.humain_chat_url, wait_until="domcontentloaded", timeout=30_000)
        logger.info("Navigated to %s", settings.humain_chat_url)

    async def stop(self) -> None:
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
        self._page = None
        self._context = None
        self._playwright = None

    # ── Accessors ───────────────────────────────────────────────────

    @property
    def page(self) -> Page:
        if self._page is None or self._page.is_closed():
            raise RuntimeError("Browser not started or page closed. Call start() first.")
        return self._page

    @property
    def is_ready(self) -> bool:
        return self._page is not None and not self._page.is_closed()

    async def ensure_page(self) -> Page:
        """Return the current page, recreating it if it was closed/crashed."""
        if self._page is not None and not self._page.is_closed():
            return self._page
        logger.warning("Page was closed – recreating...")
        if self._context is None or self._context.pages == []:
            self._page = await self._context.new_page()
        else:
            self._page = self._context.pages[0]
        await self._page.goto(settings.humain_chat_url, wait_until="domcontentloaded", timeout=30_000)
        logger.info("Recreated and navigated to %s", settings.humain_chat_url)
        return self._page

    # ── Internals ───────────────────────────────────────────────────

    async def _get_or_create_page(self) -> Page:
        if self._context.pages:
            return self._context.pages[0]
        return await self._context.new_page()
