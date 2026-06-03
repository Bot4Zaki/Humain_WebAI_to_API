"""
Structured request / response models that follow the OpenAI API contract.

Reference: https://platform.openai.com/docs/api-reference/chat
"""

from __future__ import annotations

import time
import uuid
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# ── Request models ──────────────────────────────────────────────────────


class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[dict], None] = None  # OpenAI allows string, array, or null

    class Config:
        extra = "ignore"


class ChatCompletionRequest(BaseModel):
    model: str = "humain-chat"
    messages: list[ChatMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: int = 1
    stream: bool = False
    stop: Optional[List[str]] = None
    max_tokens: Optional[int] = None
    user: Optional[str] = None

    class Config:
        extra = "ignore"


# ── Response models ─────────────────────────────────────────────────────


class CompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChoiceMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class Choice(BaseModel):
    index: int = 0
    message: ChoiceMessage
    finish_reason: Literal["stop", "length"] = "stop"


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:29]}")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = "humain-chat"
    choices: list[Choice]
    usage: CompletionUsage = Field(default_factory=CompletionUsage)


# ── Models list response ───────────────────────────────────────────────


class ModelObject(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "humain"


class ModelsListResponse(BaseModel):
    object: Literal["list"] = "list"
    data: list[ModelObject]


# ── Health response ─────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"] = "ok"
    browser_ready: bool = False
    model: str = "humain-chat"


# ── Error response ──────────────────────────────────────────────────────


class ErrorDetail(BaseModel):
    message: str
    type: str = "server_error"
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
