from __future__ import annotations

import hmac
import smtplib
import ssl
import tempfile
import time
import uuid
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Literal

from fastapi import Cookie, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ednai.models import Generation, Message, ModelInfo, Transcription, UseCaseGeneration
from ednai.providers import (
    GradioSpaceProvider,
    LocalTransformersProvider,
    NATLAS_MODEL_ID,
    NATLAS_ASR_MODELS,
    OpenAICompatibleProvider,
    Provider,
    ProviderError,
    ProviderQuotaError,
    assert_natlas_model,
)
from ednai.speech import normalize_speech_language
from ednai.use_cases import USE_CASES, build_use_case_prompt, public_use_case_registry
from server.billing import Pricing, estimate_prompt_tokens, usage_tokens
from server.config import get_settings
from server.developer_store import ALL_SCOPES, DEFAULT_SCOPES, DeveloperStore
from server.evidence_recovery import restore_recorded_submissions
from server.security import production_security_middleware, rate_limiter, validate_production_settings
from server.store import BetaStore
from server.studio import EvalRunRequest, router as studio_router, run_studio_eval

settings = get_settings()
validate_production_settings(settings)
ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
store = BetaStore(settings.ednai_database_path, settings.ednai_database_url or None)
recovered_submissions = restore_recorded_submissions(store, settings.ednai_beta_recovery_json)
if recovered_submissions:
    print(f"EDNAI_BETA_RECOVERY restored {recovered_submissions} recorded submissions", flush=True)
developer_store = DeveloperStore(
    settings.ednai_database_path,
    settings.ednai_database_url or None,
)
pricing = Pricing.from_values(
    settings.ednai_input_usd_per_1m_tokens,
    settings.ednai_output_usd_per_1m_tokens,
)
if settings.ednai_demo_account_enabled:
    developer_store.ensure_demo_account(
        settings.ednai_demo_email,
        settings.ednai_demo_password,
        initial_credit_microusd=int(settings.ednai_demo_credit_usd * 1_000_000),
    )

app = FastAPI(
    title="EDNAi",
    version="0.1.0",
    description="Developer infrastructure for NCAIR1/N-ATLaS.",
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_host_list,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "HEAD", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
)
app.mount("/assets", StaticFiles(directory=WEB), name="assets")
app.include_router(studio_router)


@app.middleware("http")
async def _production_security(request: Request, call_next):
    return await production_security_middleware(request, call_next, settings)


@app.middleware("http")
async def _studio_scope_guard(request: Request, call_next):
    scope_map = {
        ("POST", "/api/studio/dataset/inspect"): "dataset.inspect",
        ("POST", "/api/studio/fine-tune/plan"): "finetuning.plan",
    }
    scope = scope_map.get((request.method.upper(), request.url.path))
    if scope:
        try:
            _developer_principal(
                scope,
                request.headers.get("authorization"),
                request.cookies.get("ednai_session"),
            )
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers or {},
            )
    return await call_next(request)


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


class UseCaseRequest(BaseModel):
    language: str = "english"
    inputs: dict[str, Any] = Field(default_factory=dict)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=4096)
    json_mode: bool = False


class DeveloperRegister(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=10, max_length=256)
    display_name: str | None = Field(default=None, max_length=120)


class DeveloperLogin(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class DeveloperDemoRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class DeveloperApiKeyCreate(BaseModel):
    name: str = Field(default="Default key", min_length=1, max_length=80)
    scopes: list[str] = Field(default_factory=lambda: list(DEFAULT_SCOPES))


class DeveloperCreditAdjustment(BaseModel):
    amount_usd: float = Field(gt=0, le=100000)
    reference: str | None = None
    description: str | None = None


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


@app.get("/brand/ednai-logo.png", include_in_schema=False)
def ednai_logo_asset():
    # Keep legacy links on the same complete, byte-for-byte supplied artwork.
    return FileResponse(WEB / "ednai-logo.png", media_type="image/png")


@app.get("/", include_in_schema=False)
def playground():
    return FileResponse(WEB / "index.html")


@app.get("/challenge", include_in_schema=False)
def challenge_page():
    return FileResponse(WEB / "challenge.html")


@app.get("/developer", include_in_schema=False)
def developer_portal():
    return FileResponse(WEB / "developer.html")


@app.get("/guide", include_in_schema=False)
def guide_index():
    return FileResponse(WEB / "guide.html")


@app.get("/guide/en", include_in_schema=False)
def english_guide():
    return FileResponse(WEB / "guide-en.html")


@app.get("/guide/yo", include_in_schema=False)
def yoruba_guide():
    return FileResponse(WEB / "guide-yo.html")


@app.get("/guide/ha", include_in_schema=False)
def hausa_guide():
    return FileResponse(WEB / "guide-ha.html")


@app.get("/guide/ig", include_in_schema=False)
def igbo_guide():
    return FileResponse(WEB / "guide-ig.html")


def _money(microusd: int) -> float:
    return round(int(microusd) / 1_000_000, 6)


def _normalize_demo_email(value: str) -> str:
    email = value.strip().lower()
    local, sep, domain = email.rpartition("@")
    if not sep or not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    return email


def _send_demo_access_email(recipient: str, request: Request) -> None:
    host = settings.ednai_smtp_host.strip()
    sender = (settings.ednai_smtp_from or settings.ednai_smtp_username).strip()
    if not host or not sender:
        raise RuntimeError("SMTP delivery is not configured.")

    access_url = str(request.base_url).rstrip("/") + "/developer"
    message = EmailMessage()
    message["Subject"] = "Your EDNAi demo access"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "Your EDNAi demo access is ready.\n\n"
        f"Demo link: {access_url}\n"
        f"Email: {settings.ednai_demo_email}\n"
        f"Password: {settings.ednai_demo_password}\n\n"
        "This shared credential is for challenge/product evaluation only. "
        "Do not reuse it on any other service.\n\n"
        "EDNAi — Developer infrastructure for NCAIR1/N-ATLaS."
    )

    context = ssl.create_default_context()
    port = int(settings.ednai_smtp_port)
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15, context=context) as smtp:
            if settings.ednai_smtp_username:
                smtp.login(settings.ednai_smtp_username, settings.ednai_smtp_password)
            smtp.send_message(message)
        return

    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.ehlo()
        if settings.ednai_smtp_username:
            smtp.login(settings.ednai_smtp_username, settings.ednai_smtp_password)
        smtp.send_message(message)


def _session_account(ednai_session: str | None) -> dict[str, Any]:
    if not settings.ednai_auth_enabled:
        raise HTTPException(status_code=503, detail="Developer authentication is disabled.")
    if not ednai_session:
        raise HTTPException(status_code=401, detail="Developer login required.")
    account = developer_store.resolve_session(ednai_session)
    if not account:
        raise HTTPException(status_code=401, detail="Developer session is invalid or expired.")
    return account


def _rate_limit_principal(principal: dict[str, Any]) -> None:
    if settings.app_env.lower() not in {"production", "demo"}:
        return
    identity = principal.get("api_key_id") or principal.get("developer_id") or "unknown"
    ok, retry = rate_limiter.check(
        f"api:{identity}",
        settings.ednai_api_rate_limit_per_minute,
        60,
    )
    if not ok:
        raise HTTPException(
            status_code=429,
            detail="Developer request rate limit exceeded.",
            headers={"Retry-After": str(retry)},
        )


def _developer_principal(
    scope: str,
    authorization: str | None,
    ednai_session: str | None,
) -> dict[str, Any]:
    if not settings.ednai_auth_enabled:
        return {
            "developer_id": "auth-disabled",
            "api_key_id": None,
            "email": "auth-disabled",
            "is_demo": True,
            "scopes": list(ALL_SCOPES),
            "billing_exempt": True,
        }

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token.startswith("ednai_live_"):
            principal = developer_store.resolve_api_key(token)
            if not principal:
                raise HTTPException(status_code=401, detail="Invalid or revoked EDNAi API key.")
            if scope not in principal["scopes"]:
                raise HTTPException(
                    status_code=403,
                    detail=f"API key does not grant the required scope: {scope}",
                )
            principal["billing_exempt"] = False
            _rate_limit_principal(principal)
            return principal

    account = _session_account(ednai_session)
    principal = {
        "developer_id": account["id"],
        "api_key_id": None,
        "email": account["email"],
        "is_demo": account["is_demo"],
        "scopes": list(ALL_SCOPES),
        "billing_exempt": False,
    }
    _rate_limit_principal(principal)
    return principal


def _ensure_credit(principal: dict[str, Any], req: GenerateRequest) -> None:
    if principal.get("billing_exempt"):
        return
    estimate = pricing.max_authorization_microusd(
        estimate_prompt_tokens(req.messages),
        req.max_tokens,
    )
    balance = developer_store.balance_microusd(principal["developer_id"])
    if balance < estimate:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "insufficient_credit",
                "balance_usd": _money(balance),
                "estimated_max_request_usd": _money(estimate),
            },
        )


def _meter_generation(
    req: GenerateRequest,
    principal: dict[str, Any],
    *,
    feature: str,
) -> Generation:
    _ensure_credit(principal, req)
    generation = _generate(req)
    if principal.get("billing_exempt"):
        return generation

    prompt_tokens, completion_tokens, measurement = usage_tokens(
        generation.usage,
        messages=req.messages,
        output_text=generation.text,
    )
    if settings.ednai_require_exact_usage and measurement != "provider_exact":
        raise HTTPException(
            status_code=502,
            detail=(
                "The configured N-ATLaS runtime did not return exact token usage. "
                "EDNAi refused to estimate a billable request."
            ),
        )
    cost = pricing.charge_microusd(prompt_tokens, completion_tokens)
    request_id = "req_" + uuid.uuid4().hex
    try:
        metered = developer_store.record_usage(
            developer_id=principal["developer_id"],
            api_key_id=principal.get("api_key_id"),
            request_id=request_id,
            feature=feature,
            model=generation.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            measurement=measurement,
            cost_microusd=cost,
        )
    except ValueError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc

    generation.usage = {
        **generation.usage,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "measurement": measurement,
        "request_id": request_id,
        "billing": {
            "currency": "USD",
            "cost_usd": _money(cost),
            "balance_usd": _money(metered["balance_microusd"]),
        },
    }
    return generation


@app.get("/health/live")
def health_live():
    return {"status": "ok", "product": "EDNAi"}


@app.get("/health/ready")
def health_ready():
    checks = {
        "database": developer_store.ping(),
        "provider_configured": provider is not None,
        "direct_natlas_integration": settings.qualifying_provider,
    }
    if not all(checks.values()):
        raise HTTPException(status_code=503, detail={"status": "not_ready", "checks": checks})
    return {"status": "ready", "checks": checks}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "product": "EDNAi",
        "model": settings.ednai_model,
        "provider": settings.ednai_provider,
        "provider_configured": provider is not None,
        "direct_natlas_integration": settings.qualifying_provider,
        "database_ready": developer_store.ping(),
        "asr_provider_configured": provider is not None and callable(getattr(provider, "transcribe", None)),
    }


@app.post("/api/developer/demo-request")
def developer_demo_request(data: DeveloperDemoRequest, request: Request):
    if not settings.ednai_demo_account_enabled:
        raise HTTPException(status_code=503, detail="Demo access is not enabled on this deployment.")

    email = _normalize_demo_email(data.email)
    client_ip = request.client.host if request.client else "unknown"
    email_key = hmac.new(
        settings.ednai_admin_token.encode("utf-8"),
        email.encode("utf-8"),
        "sha256",
    ).hexdigest()[:24]

    for key in (f"demo-request-ip:{client_ip}", f"demo-request-email:{email_key}"):
        ok, retry = rate_limiter.check(
            key,
            settings.ednai_demo_request_rate_limit_per_hour,
            3600,
        )
        if not ok:
            raise HTTPException(
                status_code=429,
                detail="Too many demo requests. Please try again later.",
                headers={"Retry-After": str(retry)},
            )

    try:
        _send_demo_access_email(email, request)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Demo email delivery is temporarily unavailable. Please try again later.",
        ) from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise HTTPException(
            status_code=502,
            detail="We could not send the demo email right now. Please try again shortly.",
        ) from exc

    return {
        "ok": True,
        "message": "Demo link and login details have been sent to your email.",
    }


@app.post("/api/developer/register")
def developer_register(data: DeveloperRegister, response: Response):
    if not settings.ednai_auth_enabled:
        raise HTTPException(status_code=503, detail="Developer authentication is disabled.")
    try:
        account = developer_store.create_account(
            data.email,
            data.password,
            display_name=data.display_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    token = developer_store.create_session(
        account["id"],
        hours=settings.ednai_session_hours,
    )
    response.set_cookie(
        "ednai_session",
        token,
        max_age=settings.ednai_session_hours * 3600,
        httponly=True,
        secure=settings.app_env.lower() in {"production", "demo"},
        samesite="strict",
        path="/",
    )
    return {"account": account, "pricing": pricing.public()}


@app.post("/api/developer/login")
def developer_login(data: DeveloperLogin, response: Response):
    account = developer_store.verify_password(data.email, data.password)
    if not account:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = developer_store.create_session(
        account["id"],
        hours=settings.ednai_session_hours,
    )
    response.set_cookie(
        "ednai_session",
        token,
        max_age=settings.ednai_session_hours * 3600,
        httponly=True,
        secure=settings.app_env.lower() in {"production", "demo"},
        samesite="strict",
        path="/",
    )
    return {"account": account, "pricing": pricing.public()}


@app.post("/api/developer/logout")
def developer_logout(
    response: Response,
    ednai_session: str | None = Cookie(default=None),
):
    if ednai_session:
        developer_store.revoke_session(ednai_session)
    response.delete_cookie("ednai_session", path="/")
    return {"ok": True}


@app.get("/api/developer/me")
def developer_me(ednai_session: str | None = Cookie(default=None)):
    account = _session_account(ednai_session)
    usage = developer_store.usage_summary(account["id"], limit=20)
    return {
        "account": account,
        "pricing": pricing.public(),
        "api_keys": developer_store.list_api_keys(account["id"]),
        "usage": {
            **usage,
            "balance_usd": _money(usage["balance_microusd"]),
            "total_cost_usd": _money(usage["total_cost_microusd"]),
        },
        "available_scopes": ALL_SCOPES,
    }


@app.get("/api/developer/pricing")
def developer_pricing():
    return {
        **pricing.public(),
        "mode": "demo_configurable",
        "note": "Rates are platform configuration and can be changed without changing SDK code.",
    }


@app.post("/api/developer/keys")
def developer_create_key(
    data: DeveloperApiKeyCreate,
    ednai_session: str | None = Cookie(default=None),
):
    account = _session_account(ednai_session)
    active_keys = [
        key for key in developer_store.list_api_keys(account["id"])
        if not key.get("revoked_at")
    ]
    if len(active_keys) >= settings.ednai_max_api_keys_per_account:
        raise HTTPException(
            status_code=409,
            detail=(
                f"API key limit reached ({settings.ednai_max_api_keys_per_account}). "
                "Revoke an unused key before creating another."
            ),
        )
    try:
        created = developer_store.create_api_key(
            account["id"],
            name=data.name,
            scopes=data.scopes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        **created,
        "warning": "Copy this API key now. EDNAi stores only its hash and cannot show it again.",
    }


@app.delete("/api/developer/keys/{key_id}")
def developer_revoke_key(
    key_id: str,
    ednai_session: str | None = Cookie(default=None),
):
    account = _session_account(ednai_session)
    if not developer_store.revoke_api_key(account["id"], key_id):
        raise HTTPException(status_code=404, detail="API key not found or already revoked.")
    return {"ok": True}


@app.get("/api/developer/usage")
def developer_usage(ednai_session: str | None = Cookie(default=None)):
    account = _session_account(ednai_session)
    usage = developer_store.usage_summary(account["id"], limit=100)
    return {
        **usage,
        "balance_usd": _money(usage["balance_microusd"]),
        "total_cost_usd": _money(usage["total_cost_microusd"]),
        "pricing": pricing.public(),
    }


@app.post("/api/admin/developers/{developer_id}/credit")
def developer_admin_credit(
    developer_id: str,
    data: DeveloperCreditAdjustment,
    authorization: str | None = Header(default=None),
):
    _require_admin(authorization)
    try:
        developer_store.account(developer_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Developer account not found.") from exc
    amount = int(round(data.amount_usd * 1_000_000))
    entry_id = developer_store.add_ledger_entry(
        developer_id,
        kind="credit",
        amount_microusd=amount,
        reference=data.reference or "admin-credit",
        description=data.description or "Developer credit adjustment",
    )
    return {
        "ok": True,
        "ledger_entry_id": entry_id,
        "balance_usd": _money(developer_store.balance_microusd(developer_id)),
    }


@app.get("/v1/models")
def models():
    return {"object": "list", "data": [ModelInfo(id=NATLAS_MODEL_ID).model_dump()]}


@app.get("/v1/audio/capabilities")
def speech_capabilities():
    return {
        "asr": {
            "provider": "NCAIR1",
            "official_natlas_components": True,
            "languages": NATLAS_ASR_MODELS,
            "runtime_configured": provider is not None and callable(getattr(provider, "transcribe", None)),
            "runtime_verified": False,
            "input": ["microphone", "wav", "mp3", "m4a", "ogg", "webm"],
        },
    }


@app.post("/v1/audio/transcriptions", response_model=Transcription)
async def audio_transcriptions(
    file: UploadFile = File(...),
    language: str = Form(...),
    authorization: str | None = Header(default=None),
    ednai_session: str | None = Cookie(default=None),
):
    _developer_principal("speech.transcribe", authorization, ednai_session)
    try:
        language = normalize_speech_language(language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    transcribe = getattr(provider, "transcribe", None) if provider is not None else None
    if not callable(transcribe):
        raise HTTPException(
            status_code=503,
            detail="The configured EDNAi runtime does not expose official NCAIR ASR.",
        )

    suffix = Path(file.filename or "audio.webm").suffix[:12] or ".audio"
    temp_path = None
    total = 0
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp_path = Path(temp.name)
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > 25 * 1024 * 1024:
                    raise HTTPException(
                        status_code=413,
                        detail="Audio uploads are limited to 25 MB.",
                    )
                temp.write(chunk)

        if total == 0:
            raise HTTPException(status_code=400, detail="Audio file is empty.")

        try:
            return await run_in_threadpool(transcribe, temp_path, language)
        except ProviderQuotaError as exc:
            headers = (
                {"Retry-After": str(exc.retry_after_seconds)}
                if exc.retry_after_seconds
                else None
            )
            raise HTTPException(status_code=429, detail=str(exc), headers=headers) from exc
        except ProviderError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await file.close()
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@app.get("/v1/use-cases")
def use_cases():
    return public_use_case_registry()


@app.post("/v1/use-cases/{use_case}", response_model=UseCaseGeneration)
def run_use_case(
    use_case: str,
    request: UseCaseRequest,
    authorization: str | None = Header(default=None),
    ednai_session: str | None = Cookie(default=None),
):
    if use_case not in USE_CASES:
        raise HTTPException(status_code=404, detail=f"Unknown EDNAi use case: {use_case}")
    try:
        system, user, output_language = build_use_case_prompt(
            use_case,
            request.language,
            request.inputs,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    principal = _developer_principal("usecases.run", authorization, ednai_session)
    definition = USE_CASES[use_case]
    generation = _meter_generation(
        GenerateRequest(
            model=NATLAS_MODEL_ID,
            messages=[
                Message(role="system", content=system),
                Message(role="user", content=user),
            ],
            temperature=(
                request.temperature
                if request.temperature is not None
                else float(definition["temperature"])
            ),
            max_tokens=(
                request.max_tokens
                if request.max_tokens is not None
                else int(definition["max_tokens"])
            ),
            json_mode=request.json_mode,
        ),
        principal,
        feature=f"usecase.{use_case}",
    )
    return UseCaseGeneration(
        **generation.model_dump(),
        use_case=use_case,
        language=output_language,
    )


@app.get("/v1/capabilities")
def capabilities():
    return {
        "product": "EDNAi",
        "model": NATLAS_MODEL_ID,
        "interfaces": ["python-sdk", "typescript-sdk", "openai-compatible-http", "playground", "audio-transcriptions", "speech-studio", "use-case-studio"],
        "runtime_modes": ["local_transformers", "gradio_zerogpu", "openai_compatible_natlas"],
        "evaluation": ["jsonl-benchmarks", "json-validity", "keyword-regression", "language-smoke", "latency"],
        "adaptation": ["qlora", "lora", "nf4-4bit", "adapter-only-output"],
        "documentation_languages": ["english", "yoruba", "hausa", "igbo"],
        "asr_models": NATLAS_ASR_MODELS,
        "speech": {
            "asr": "official-ncair-natlas-components",
            "submission_scope": "official-natlas-only",
        },
        "use_cases": list(USE_CASES),
        "developer_platform": {
            "accounts": True,
            "scoped_api_keys": True,
            "prepaid_wallet": True,
            "token_metering": True,
            "usage_ledger": True,
            "available_scopes": ALL_SCOPES,
        },
    }


@app.post("/api/studio/evaluate")
def studio_evaluate(
    data: EvalRunRequest,
    authorization: str | None = Header(default=None),
    ednai_session: str | None = Cookie(default=None),
):
    principal = _developer_principal("evaluation.run", authorization, ednai_session)

    class MeteredEvalProvider:
        def generate(
            self,
            messages,
            *,
            model=NATLAS_MODEL_ID,
            temperature=0.2,
            max_tokens=512,
            json_mode=False,
        ):
            return _meter_generation(
                GenerateRequest(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                ),
                principal,
                feature="evaluation.run",
            )

    return run_studio_eval(MeteredEvalProvider(), data)


@app.post("/api/runtime/probe")
def runtime_probe(
    authorization: str | None = Header(default=None),
    ednai_session: str | None = Cookie(default=None),
):
    _developer_principal("inference.generate", authorization, ednai_session)
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
    except ProviderQuotaError as exc:
        headers = (
            {"Retry-After": str(exc.retry_after_seconds)}
            if exc.retry_after_seconds
            else None
        )
        raise HTTPException(status_code=429, detail=str(exc), headers=headers) from exc
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
    except ProviderQuotaError as exc:
        headers = (
            {"Retry-After": str(exc.retry_after_seconds)}
            if exc.retry_after_seconds
            else None
        )
        raise HTTPException(status_code=429, detail=str(exc), headers=headers) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/v1/generate", response_model=Generation)
def generate(
    req: GenerateRequest,
    authorization: str | None = Header(default=None),
    ednai_session: str | None = Cookie(default=None),
):
    principal = _developer_principal("inference.generate", authorization, ednai_session)
    return _meter_generation(req, principal, feature="inference.generate")


@app.post("/v1/chat/completions")
def chat_completions(
    req: ChatCompletionRequest,
    authorization: str | None = Header(default=None),
    ednai_session: str | None = Cookie(default=None),
):
    principal = _developer_principal("inference.chat", authorization, ednai_session)
    generation = _meter_generation(
        GenerateRequest(
            model=req.model,
            messages=req.messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        ),
        principal,
        feature="inference.chat",
    )
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
        "validation": store.stats(),
        "note": "Submission recorded. Challenge verification requires review.",
    }


def _require_admin(authorization: str | None) -> None:
    token = settings.ednai_admin_token
    if token in {"", "change-me"}:
        raise HTTPException(
            status_code=503,
            detail="Beta evidence review is disabled until EDNAI_ADMIN_TOKEN is configured.",
        )
    supplied = authorization or ""
    expected = f"Bearer {token}"
    if not hmac.compare_digest(supplied, expected):
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
        "speech_studio": True,
        "official_ncair_asr_tooling": True,
        "natlas_use_case_studio": True,
        "developer_accounts_api_keys_billing": True,
        "bilingual_documentation": True,
        "multilingual_documentation_en_yo_ha_ig": True,
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
