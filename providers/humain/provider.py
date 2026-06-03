import asyncio
import logging
import json
import httpx
import re
from typing import TYPE_CHECKING, List, Optional, AsyncGenerator

from app.config import settings
from app.schemas import ChatMessage
from providers.base import BaseProvider
from providers.exceptions import AuthenticationError

if TYPE_CHECKING:
    from app.browser import BrowserManager

logger = logging.getLogger("humain-webai-to-api.humain")

class HumainProvider(BaseProvider):
    def __init__(self, browser_manager: 'BrowserManager') -> None:
        self._browser = browser_manager
        self._token: Optional[str] = None
        self._cookies: dict = {}
        self._conversation_id: Optional[str] = None

    async def _fetch_auth_state(self):
        """Silently fetch the Bearer token and WAF cookies using Playwright."""
        page = await self._browser.ensure_page()
        
        token = None
        async def handle_request(route):
            nonlocal token
            if "humain.ai" in route.request.url:
                auth = route.request.headers.get("authorization")
                if auth:
                    token = auth
            await route.continue_()
            
        await page.route("**/*", handle_request)
        
        try:
            logger.info("Fetching native API auth state...")
            await page.goto("https://chat.humain.ai/")
            # Wait for up to 10 seconds to capture token from background requests
            for _ in range(20):
                if token:
                    break
                await asyncio.sleep(0.5)
                
            if not token:
                logger.warning("Failed to automatically extract token. Are you logged in?")
                return

            self._token = token
            
            raw_cookies = await page.context.cookies()
            self._cookies = {c['name']: c['value'] for c in raw_cookies}
            logger.info("Successfully extracted API auth state.")
        except Exception as e:
            logger.error(f"Failed to fetch auth state: {e}")
        finally:
            await page.unroute("**/*")

    async def is_authenticated(self, page=None) -> bool:
        if not self._token:
            await self._fetch_auth_state()
        return bool(self._token)

    async def chat(self, messages: List[ChatMessage]) -> str:
        full = ""
        async for chunk in self.chat_stream(messages):
            full += chunk
        return full

    async def _send_api_request(self, message: str, conversation_id: str = None):
        """Sends a single streaming request to the Humain API."""
        if not self._token:
            await self._fetch_auth_state()
            if not self._token:
                raise AuthenticationError("Not logged in or failed to extract token.")

        headers = {
            "accept": "text/event-stream",
            "authorization": self._token,
            "content-type": "application/json",
            "origin": "https://chat.humain.ai",
            "referer": "https://chat.humain.ai/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }

        # Auto-detect if the user wants to search the web
        msg_lower = message.lower()
        wants_search = any(kw in msg_lower for kw in [
            "search the web", "search internet", "search the internet", 
            "google", "look up", "lookup", "search for", "latest news"
        ])

        payload = {
            "message": message,
            "context_enabled": True,
            "web_search": wants_search
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id
            payload["assistant"] = None

        logger.info(f"Sending request with conversation_id: {conversation_id}")
        
        import httpx_sse
        try:
            async with httpx.AsyncClient(cookies=self._cookies, headers=headers, timeout=60.0) as client:
                async with client.stream("POST", "https://api-allam.humain.ai/v1/message", json=payload) as response:
                    if response.status_code == 401:
                        logger.warning("Humain API Token Expired (401). Triggering background refresh...")
                        self._token = None
                        asyncio.create_task(self._fetch_auth_state())
                        yield "\n\n[System Notice: The Humain session token expired. I am refreshing it automatically in the background. Please re-send your message in a few seconds!]"
                        return
                    elif response.status_code != 200:
                        text = await response.aread()
                        logger.error(f"Humain API returned {response.status_code}: {text}")
                        yield f"\n\n[Humain API Error {response.status_code}: {text}]"
                        return

                    event_source = httpx_sse.EventSource(response)
                    async for sse in event_source.aiter_sse():
                        if sse.data == "[DONE]":
                            break
                        
                        if sse.event == "tool_status":
                            try:
                                data = json.loads(sse.data)
                                if data.get("status") == "STARTED" and data.get("tool_name") == "web_search":
                                    query = data.get("query", "")
                                    yield f"\n*(Searching the web for: {query})*\n"
                            except json.JSONDecodeError:
                                pass

                        if sse.event == "start":
                            try:
                                data = json.loads(sse.data)
                                if "conversation_id" in data:
                                    self._conversation_id = data["conversation_id"]
                            except json.JSONDecodeError:
                                pass

                        if sse.event == "message":
                            try:
                                data = json.loads(sse.data)
                                if "content" in data:
                                    yield data["content"]
                            except json.JSONDecodeError:
                                continue
        except httpx_sse.SSEError as e:
            logger.error(f"SSE Error: {e}")
            yield f"\n\n[SSE Error: {e}]"

    async def chat_stream(self, messages: List[ChatMessage]) -> AsyncGenerator[str, None]:
        if not await self.is_authenticated():
            raise AuthenticationError("Not logged in or failed to extract token.")

        def _text(val):
            if val is None: return ""
            if isinstance(val, list): txt = "\n".join(part.get("text", "") for part in val if isinstance(part, dict) and "text" in part)
            else: txt = str(val)
            txt = re.sub(r'\[[a-zA-Z]{3} \d{4}-\d{2}-\d{2} \d{2}:\d{2} GMT[+-]\d{1,2}\]\s*', '', txt)
            return txt

        # Find if user manually requested a reset
        is_reset_turn = False
        last_reset_idx = -1
        for i, msg in enumerate(messages):
            if _text(msg.content).strip().lower() in ["/reset", "/new"]:
                last_reset_idx = i
                if i == len(messages) - 1:
                    is_reset_turn = True

        if is_reset_turn:
            self._conversation_id = None
            yield "Humain chat session has been explicitly reset."
            return

        if last_reset_idx != -1:
            sys_msg = messages[0] if messages and messages[0].role == "system" else None
            messages = messages[last_reset_idx + 1:]
            
            # Drop the assistant's generic reply to the reset command so the history is clean
            if messages and messages[0].role == "assistant" and "explicitly reset" in str(messages[0].content):
                messages = messages[1:]
                
            if sys_msg and (not messages or messages[0].role != "system"):
                messages.insert(0, sys_msg)

        if len(messages) <= 2:
            self._conversation_id = None

        final_msg = _text(messages[-1].content)

        if len(messages) <= 2 or not self._conversation_id:
            # Yield immediately to prevent OpenClaw 10-second timeout on fresh sessions
            yield "*(Initializing Humain session...)*\n\n"
            
            # We are starting a fresh context. We must send the system context first to establish the persona.
            context_parts = []
            for msg in messages[:-1]:
                context_parts.append(f"[{msg.role.upper()}]: {_text(msg.content)}")

            if context_parts:
                context_prompt = "CONTEXT:\n" + "\n".join(context_parts)
                max_length = 15500
                if len(context_prompt) > max_length:
                    logger.warning("Prompt too long (%d chars), truncating to %d", len(context_prompt), max_length)
                    keep_start = 3000
                    keep_end = max_length - keep_start - 100
                    trunc_notice = "\n\n... [CONTENT TRUNCATED DUE TO 16K LIMIT] ...\n\n"
                    context_prompt = context_prompt[:keep_start] + trunc_notice + context_prompt[-keep_end:]

                # Force a 1-token generation to drastically reduce Humain API latency
                context_prompt += "\n\n(Acknowledge this context by replying with exactly one word: 'OK')"

                # Turn 1: Send the context and ignore the stream output, just capture the conversation_id
                async for _ in self._send_api_request(context_prompt, conversation_id=None):
                    pass

                # Turn 2: Send the actual newest user message using the newly generated conversation_id
                async for chunk in self._send_api_request(final_msg, conversation_id=self._conversation_id):
                    yield chunk
            else:
                # Only 1 message (no context), just send it directly
                async for chunk in self._send_api_request(final_msg, conversation_id=None):
                    yield chunk
        else:
            # Middle of an ongoing session: simply inject the user message into the existing backend session!
            # This is infinitely faster and completely bypasses the 16k limit for follow-ups!
            async for chunk in self._send_api_request(final_msg, conversation_id=self._conversation_id):
                yield chunk
