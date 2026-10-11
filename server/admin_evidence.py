"""Cookie-protected evidence review and reproducible snapshot exports."""
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from server.evidence_pdf import validation_pdf

router = APIRouter()
COOKIE = "ednai_admin_session"


def main():
    from server import main as application
    return application


def require_session(request):
    token = main().settings.ednai_admin_token
    if token in {"", "change-me"}:
        raise HTTPException(503, "Configure EDNAI_ADMIN_TOKEN to enable evidence administration.")
    supplied = request.cookies.get(COOKIE, "")
    try:
        payload, signature = supplied.rsplit(".", 1)
        expiry, nonce = payload.split(":", 1)
        expected = hmac.new(token.encode(), payload.encode(), hashlib.sha256).hexdigest()
        valid = hmac.compare_digest(signature, expected) and int(expiry) > time.time()
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise HTTPException(401, "Admin session expired or missing. Sign in again.")


class Login(BaseModel):
    token: str = Field(min_length=1, max_length=500)


@router.get("/challenge/admin", include_in_schema=False)
def admin_page():
    return FileResponse(main().WEB / "challenge-admin.html", headers={"Cache-Control": "no-store"})


@router.post("/api/admin/session")
def login(data: Login, request: Request):
    main()._require_admin("Bearer " + data.token)
    payload = f"{int(time.time()) + 3600}:{secrets.token_hex(16)}"
    signature = hmac.new(data.token.encode(), payload.encode(), hashlib.sha256).hexdigest()
    response = Response(content='{"ok":true}', media_type="application/json")
    response.set_cookie(COOKIE, payload + "." + signature, max_age=3600, httponly=True,
                        secure=request.url.scheme == "https", samesite="strict", path="/api/admin")
    return response


@router.delete("/api/admin/session")
def logout():
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, path="/api/admin")
    return response


def snapshot():
    records = jsonable_encoder(main().store.report_records())
    return {"generated_at": datetime.now(timezone.utc).isoformat(),
            "project": "EDNAi", "problem_statement": "Developer Infrastructure",
            "model": "NCAIR1/N-ATLaS", "validation": main().store.stats(), "records": records}


@router.get("/api/admin/evidence")
def evidence(request: Request):
    require_session(request)
    return snapshot()


@router.post("/api/admin/evidence/{evidence_id}/verify")
def verify(evidence_id: str, request: Request):
    require_session(request)
    records = main().store.report_records()
    record = next((r for r in records if r["id"] == evidence_id), None)
    if not record:
        raise HTTPException(404, "Evidence not found")
    if not record["test_details"].get("authenticity_confirmed"):
        raise HTTPException(400, "Detailed actual-test evidence is missing. Ask the tester to submit the expanded form.")
    try:
        return main().store.verify_external(evidence_id)
    except KeyError:
        raise HTTPException(400, "Only consented external feedback can be verified")


@router.get("/api/admin/evidence/report.pdf")
def pdf_report(request: Request):
    require_session(request)
    return Response(validation_pdf(snapshot()), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="EDNAi_Validation_Evidence.pdf"'})


@router.get("/api/admin/evidence/report.json")
def json_report(request: Request):
    require_session(request)
    return Response(json.dumps(snapshot(), ensure_ascii=False, indent=2).encode(), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="EDNAi_Validation_Evidence.json"'})
