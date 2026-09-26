from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


Role = Literal["system", "user", "assistant"]


class Message(BaseModel):
    role: Role
    content: str


class Generation(BaseModel):
    text: str
    model: str
    provider: str | None = None
    finish_reason: str | None = None
    latency_ms: float | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "NCAIR1"
    family: str = "N-ATLaS"
    supported_languages: list[str] = Field(
        default_factory=lambda: ["english", "yoruba", "hausa", "igbo"]
    )
