"""
FastAPI route handlers – OpenAI-compatible endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

import json

from app.deps import browser_manager, limiter
from app.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    HealthResponse,
    ModelsListResponse,
    ModelObject,
    Choice,
    ChoiceMessage,
)
from providers.humain.provider import HumainProvider

logger = logging.getLogger("humain-webai-to-api.routes")

router = APIRouter()

# Lazy-initialised provider singleton
_provider: Optional[HumainProvider] = None


def _get_provider() -> HumainProvider:
    global _provider
    if _provider is None:
        _provider = HumainProvider(browser_manager)
    return _provider


# ── GET /health ─────────────────────────────────────────────────────────


@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def health():
    ready = browser_manager.is_ready
    return HealthResponse(
        status="ok" if ready else "degraded",
        browser_ready=ready,
    )


# ── GET /v1/models ──────────────────────────────────────────────────────


@router.get("/v1/models", response_model=ModelsListResponse, tags=["models"])
async def list_models():
    return ModelsListResponse(
        data=[
            ModelObject(id="humain-chat", owned_by="humain"),
        ]
    )


# ── POST /v1/chat/completions ──────────────────────────────────────────


@router.post(
    "/v1/chat/completions",
    response_model=ChatCompletionResponse,
    responses={
        400: {"description": "Bad request – streaming not supported or invalid input"},
        502: {"description": "Provider error – HUMAIN interaction failed"},
    },
    tags=["chat"],
)
@limiter.limit("10/minute")
async def chat_completions(request: Request):
    """
    Send a chat message to HUMAIN and return an OpenAI-compatible response.

    Currently supports **non-streaming only** (`stream=false`).
    """
    # DEBUG: read raw body first so we can see what OpenClaw sends
    try:
        raw = await request.json()
        logger.info("Raw request body keys: %s", list(raw.keys()))
    except Exception as exc:
        logger.warning("Could not parse raw JSON: %s", exc)
        raw = {}

    try:
        body = ChatCompletionRequest(**raw)
    except Exception as exc:
        logger.error("Pydantic validation failed for keys %s: %s", list(raw.keys()), exc)
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "message": f"Validation error: {exc}",
                    "type": "invalid_request_error",
                    "code": "validation_error",
                }
            },
        )

    if body.stream:
        return StreamingResponse(
            _sse_stream(body),
            media_type="text/event-stream",
        )

    provider = _get_provider()

    try:
        reply_text = await provider.chat(body.messages)
    except Exception as exc:
        logger.exception("Provider error")
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "message": str(exc),
                    "type": "provider_error",
                    "code": getattr(exc, "code", None) or exc.__class__.__name__,
                }
            },
        )

    return ChatCompletionResponse(
        model=body.model,
        choices=[
            Choice(
                message=ChoiceMessage(content=reply_text),
            )
        ],
    )


async def _sse_stream(body: ChatCompletionRequest):
    """Iterate over the provider stream and emit SSE chunks."""
    provider = _get_provider()
    try:
        async for chunk_text in provider.chat_stream(body.messages):
            chunk = {
                "id": "chatcmpl-humain",
                "object": "chat.completion.chunk",
                "created": 0,
                "model": body.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": chunk_text},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            
        # Final empty chunk to signal stop
        final_chunk = {
            "id": "chatcmpl-humain",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": body.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        
    except Exception as exc:
        logger.exception("Streaming provider error")
        error_chunk = {
            "id": "chatcmpl-humain",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": body.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": f"\n\n[Error: {exc}]"},
                    "finish_reason": "stop",
                }
            ],
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        
    yield "data: [DONE]\n\n"
