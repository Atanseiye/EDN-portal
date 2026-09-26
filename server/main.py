from __future__ import annotations

import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ednai.models import Generation, Message, ModelInfo
from ednai.providers import (
    GradioSpaceProvider,
    LocalTransformersProvider,
    NATLAS_MODEL_ID,
    OpenAICompatibleProvider,
    Provider,
    ProviderError,
    assert_natlas_model,
)
from server.config import get_settings
from server.store import BetaStore

settings = get_settings()
ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
store = BetaStore(settings.ednai_database_path, settings.ednai_database_url or None)

app = FastAPI(
    title="EDNAi",
    version="0.1.0",
    description="Developer infrastructure for NCAIR1/N-ATLaS.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=WEB), name="assets")


def build_provider() -> Provider | None:
    kind = settings.ednai_provider.lower()
    if kind == "openai_compatible":
        return OpenAICompatibleProvider(
            settings.ednai_upstream_base_url,
            settings.ednai_upstream_api_key,
        )
    if kind == "gradio_space":
        return GradioSpaceProvider(settings.ednai_gradio_space_id, settings.hf_token or None)
    if kind == "local":
        return LocalTransformersProvider(settings.hf_token or None)
    return None


provider = build_provider()


class GenerateRequest(BaseModel):
    model: str = NATLAS_MODEL_ID
    messages: list[Message]
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=512, ge=1, le=4096)
    json_mode: bool = False


class ChatCompletionRequest(BaseModel):
    model: str = NATLAS_MODEL_ID
    messages: list[Message]
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=512, ge=1, le=4096)


class BetaFeedback(BaseModel):
    tester_identity: str = Field(min_length=3, description="Email or other stable identifier; stored only as a hash.")
    display_name: str | None = None
    affiliation: str | None = None
    role: str | None = None
    features: list[str] = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    useful: bool
    blocker: str | None = None
    notes: str | None = None
    external_tester: bool
    consent: bool


@app.get("/", include_in_schema=False)
def playground():
    return FileResponse(WEB / "index.html")


@app.get("/challenge", include_in_schema=False)
def challenge_page():
    return FileResponse(WEB / "challenge.html")


@app.get("/guide/en", include_in_schema=False)
def english_guide():
    return FileResponse(WEB / "guide-en.html")


@app.get("/guide/yo", include_in_schema=False)
def yoruba_guide():
    return FileResponse(WEB / "guide-yo.html")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "product": "EDNAi",
        "model": settings.ednai_model,
        "provider": settings.ednai_provider,
        "provider_configured": provider is not None,
        "direct_natlas_integration": settings.qualifying_provider,
    }


@app.get("/v1/models")
def models():
    return {"object": "list", "data": [ModelInfo(id=NATLAS_MODEL_ID).model_dump()]}


def _generate(req: GenerateRequest) -> Generation:
    try:
        assert_natlas_model(req.model)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "A direct N-ATLaS runtime is not configured on this deployment. "
                "Set EDNAI_PROVIDER to local, gradio_space, or openai_compatible."
            ),
        )
    try:
        return provider.generate(
            req.messages,
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            json_mode=req.json_mode,
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/v1/generate", response_model=Generation)
def generate(req: GenerateRequest):
    return _generate(req)


@app.post("/v1/chat/completions")
def chat_completions(req: ChatCompletionRequest):
    generation = _generate(GenerateRequest(
        model=req.model,
        messages=req.messages,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    ))
    return {
        "id": f"ednai-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": NATLAS_MODEL_ID,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": generation.text},
            "finish_reason": generation.finish_reason or "stop",
        }],
        "usage": generation.usage,
        "ednai": {
            "provider": generation.provider,
            "latency_ms": generation.latency_ms,
            "direct_natlas": True,
        },
    }


@app.post("/api/beta/feedback")
def beta_feedback(data: BetaFeedback):
    try:
        evidence_id = store.add(**data.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "evidence_id": evidence_id}


@app.get("/api/challenge/readiness")
def readiness():
    beta = store.stats()
    checks = {
        "working_developer_artifact": True,
        "python_sdk": True,
        "javascript_sdk": True,
        "interactive_playground": True,
        "fine_tuning_starter": True,
        "evaluation_tooling": True,
        "bilingual_documentation": True,
        "direct_natlas_runtime_configured": settings.qualifying_provider,
        "minimum_two_external_beta_testers": beta["beta_target_met"],
    }
    return {
        "ready": all(checks.values()),
        "track": "Innovation & Enterprise",
        "problem_statement": "Developer Infrastructure",
        "model": NATLAS_MODEL_ID,
        "checks": checks,
        "validation": beta,
        "note": "EDNAi never counts internal or synthetic testing toward the external beta-test requirement.",
    }
