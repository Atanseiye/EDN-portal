from __future__ import annotations

import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
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


@app.head("/", include_in_schema=False)
def root_head():
    return Response(status_code=200)


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


@app.get("/v1/capabilities")
def capabilities():
    return {
        "product": "EDNAi",
        "model": NATLAS_MODEL_ID,
        "interfaces": ["python-sdk", "typescript-sdk", "openai-compatible-http", "playground"],
        "runtime_modes": ["local_transformers", "gradio_zerogpu", "openai_compatible_natlas"],
        "evaluation": ["jsonl-benchmarks", "json-validity", "keyword-regression", "language-smoke", "latency"],
        "adaptation": ["qlora", "lora", "nf4-4bit", "adapter-only-output"],
        "documentation_languages": ["english", "yoruba"],
        "asr_models": {
            "english": "NCAIR1/NigerianAccentedEnglish",
            "yoruba": "NCAIR1/Yoruba-ASR",
            "hausa": "NCAIR1/Hausa-ASR",
            "igbo": "NCAIR1/Igbo-ASR",
        },
    }


@app.post("/api/runtime/probe")
def runtime_probe():
    if provider is None:
        raise HTTPException(status_code=503, detail="No direct N-ATLaS runtime is configured.")
    started = time.perf_counter()
    try:
        generation = provider.generate(
            [Message(role="user", content="Reply with exactly: EDNAI_OK")],
            model=NATLAS_MODEL_ID,
            temperature=0,
            max_tokens=16,
            json_mode=False,
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if generation.model != NATLAS_MODEL_ID:
        raise HTTPException(status_code=502, detail="Runtime returned an unexpected model identity.")
    return {
        "ok": bool(generation.text.strip()),
        "model": generation.model,
        "provider": generation.provider,
        "output": generation.text.strip(),
        "latency_ms": generation.latency_ms or round((time.perf_counter() - started) * 1000, 2),
        "provenance_verified": True,
    }


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
    return {
        "ok": True,
        "evidence_id": evidence_id,
        "status": "pending_review",
        "note": "External-tester evidence is counted only after review.",
    }


def _require_admin(authorization: str | None) -> None:
    token = settings.ednai_admin_token
    if token in {"", "change-me"}:
        raise HTTPException(
            status_code=503,
            detail="Beta evidence review is disabled until EDNAI_ADMIN_TOKEN is configured.",
        )
    if authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/api/admin/beta/pending")
def beta_pending(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    return {"data": store.pending()}


@app.post("/api/admin/beta/{evidence_id}/verify")
def beta_verify(evidence_id: str, authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    try:
        return {"ok": True, "verification": store.verify_external(evidence_id)}
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Evidence not found or it was not submitted as consented external feedback.",
        )


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
        "note": "EDNAi counts only reviewed, consented external developers; self-declared or synthetic submissions do not satisfy the beta requirement.",
    }
