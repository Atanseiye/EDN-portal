from pathlib import Path
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.models import AdviceRequest, AdviceResponse, ComplaintDraftRequest, ComplaintDraftResponse, FeedbackRequest, Language
from app.services.advice import AdviceService
from app.services.asr import ASRError, NAtlasASR

settings = get_settings()
service = AdviceService(settings)
asr = NAtlasASR(settings)
static_dir = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="PowerRights NG",
    version="0.2.0",
    description="Voice-first Nigerian electricity consumer rights and complaint-navigation assistant powered by N-ATLaS.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(static_dir / "index.html")


@app.get("/challenge", include_in_schema=False)
def challenge_page():
    return FileResponse(static_dir / "challenge.html")


@app.get("/health")
def health():
    stats = service.validation.stats()
    challenge_ready = (
        settings.challenge_model_ready
        and settings.challenge_asr_ready
        and stats["validation_target_met"]
    )
    return {
        "status": "ok",
        "environment": settings.app_env,
        "natlas_provider": settings.natlas_provider,
        "asr_provider": settings.asr_provider,
        "natlas_model": settings.natlas_model,
        "database_persistence": settings.persistent_validation_ready,
        "structured_validation_audit_log": settings.validation_audit_log_ready,
        "eligible_voice_interactions": stats["competition_eligible_voice_interactions"],
        "validation_target": stats["validation_target"],
        "challenge_ready": challenge_ready,
    }


@app.get("/api/v1/challenge/readiness")
def challenge_readiness():
    stats = service.validation.stats()
    checks = {
        "working_technical_artifact": True,
        "official_natlas_llm_configured": settings.challenge_model_ready,
        "official_natlas_asr_configured": settings.challenge_asr_ready,
        "minimum_50_documented_real_voice_interactions": stats["validation_target_met"],
        "mock_and_grounded_fallback_traffic_excluded": True,
        "official_source_grounding": True,
        "same_language_input_output": True,
        "state_aware_regulator_routing": True,
        "validation_consent_and_audit_trail": settings.validation_audit_log_ready,
        "technical_documentation_in_repository": True,
    }
    qualifying = (
        checks["working_technical_artifact"]
        and checks["official_natlas_llm_configured"]
        and checks["official_natlas_asr_configured"]
        and checks["minimum_50_documented_real_voice_interactions"]
    )
    return {
        "ready": qualifying,
        "track": "Innovation & Enterprise",
        "problem_statement": "Voice-First Access",
        "checks": checks,
        "validation": stats,
        "required_models": {
            "llm": "NCAIR1/N-ATLaS",
            "english_asr": "NCAIR1/NigerianAccentedEnglish",
            "yoruba_asr": "NCAIR1/Yoruba-ASR",
            "hausa_asr": "NCAIR1/Hausa-ASR",
            "igbo_asr": "NCAIR1/Igbo-ASR",
        },
        "note": (
            "Submission readiness stays false until the live deployment uses genuine N-ATLaS LLM and official N-ATLaS ASR, "
            "and at least 50 consented real-user voice interactions have traversed that exact model path."
        ),
    }


@app.post("/api/v1/advice", response_model=AdviceResponse)
async def advice(req: AdviceRequest):
    return await service.advise(req)


@app.post("/api/v1/voice/advice", response_model=AdviceResponse)
async def voice_advice(
    audio: UploadFile = File(...),
    language: Language = Form(...),
    state: str | None = Form(default=None),
    disco: str | None = Form(default=None),
    session_id: str | None = Form(default=None),
    validation_consent: bool = Form(default=False),
):
    if not settings.challenge_asr_ready:
        raise HTTPException(
            status_code=503,
            detail="Official N-ATLaS ASR is not connected on this deployment. Voice validation is intentionally disabled rather than using mock transcription."
        )
    content = await audio.read()
    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    try:
        transcript = asr.transcribe(content, language, suffix=suffix)
    except ASRError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    req = AdviceRequest(message=transcript, language=language, state=state, disco=disco, session_id=session_id)
    result = await service.advise(
        req,
        channel="voice",
        asr_provider=settings.asr_provider,
        validation_consent=validation_consent,
    )
    payload = result.model_dump()
    payload["summary"] = f"Transcript: {transcript}\n\n{payload['summary']}"
    return AdviceResponse(**payload)


@app.post("/api/v1/complaint", response_model=ComplaintDraftResponse)
async def complaint(req: ComplaintDraftRequest):
    return await service.draft_complaint(req)


@app.post("/api/v1/feedback")
def feedback(req: FeedbackRequest):
    try:
        service.validation.add_feedback(req)
    except KeyError:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return {"ok": True}


def _require_admin(auth: str | None):
    if settings.admin_token in {"", "change-me"}:
        raise HTTPException(status_code=503, detail="Admin API is disabled until ADMIN_TOKEN is configured.")
    expected = f"Bearer {settings.admin_token}"
    if not auth or auth != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/api/v1/admin/validation/stats")
def validation_stats(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    return service.validation.stats()


@app.get("/api/v1/admin/validation/export.csv", response_class=PlainTextResponse)
def validation_export(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    return PlainTextResponse(
        service.validation.export_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=powerrights-validation.csv"},
    )
