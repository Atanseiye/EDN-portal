from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("ednai.security")


def validate_production_settings(settings: Any) -> None:
    if settings.app_env.lower() != "production":
        return

    errors: list[str] = []
    if not settings.ednai_auth_enabled:
        errors.append("EDNAI_AUTH_ENABLED must be true in production.")
    if not settings.ednai_database_url:
        errors.append("EDNAI_DATABASE_URL is required in production; ephemeral SQLite is not allowed.")
    if settings.ednai_admin_token in {"", "change-me"} or len(settings.ednai_admin_token) < 32:
        errors.append("EDNAI_ADMIN_TOKEN must be a strong non-default secret (32+ chars).")
    if settings.ednai_provider == "gradio_space" and not settings.hf_token:
        errors.append("HF_TOKEN is required for authenticated hosted N-ATLaS inference.")
    if "*" in settings.cors_origin_list:
        errors.append("Wildcard CORS is not allowed in production.")
    if "*" in settings.trusted_host_list:
        errors.append("Wildcard trusted hosts are not allowed in production.")
    if settings.ednai_demo_account_enabled and not settings.ednai_allow_public_demo_account:
        errors.append(
            "Public demo account is enabled in production. Set EDNAI_ALLOW_PUBLIC_DEMO_ACCOUNT=true "
            "only for a dedicated demo environment."
        )
    if settings.ednai_pricing_mode != "production":
        errors.append("EDNAI_PRICING_MODE must be 'production' before serving billable real users.")
    if not settings.ednai_require_exact_usage:
        errors.append("EDNAI_REQUIRE_EXACT_USAGE must be true in production.")

    if errors:
        raise RuntimeError("Unsafe EDNAi production configuration:\n- " + "\n- ".join(errors))


@dataclass
class _Bucket:
    hits: deque[float]


class FixedWindowLimiter:
    """Single-instance safety limiter. Put APIM/Front Door/Redis in front for distributed limits."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= limit:
                retry = max(1, int(window_seconds - (now - q[0])))
                return False, retry
            q.append(now)
            return True, 0


rate_limiter = FixedWindowLimiter()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


async def production_security_middleware(request: Request, call_next, settings: Any):
    request_id = request.headers.get("x-request-id") or "req_" + uuid.uuid4().hex
    request.state.request_id = request_id

    # Global body ceiling; audio has its own stricter content handling.
    length = request.headers.get("content-length")
    if length:
        try:
            size = int(length)
            max_size = 32 * 1024 * 1024 if request.url.path.startswith("/v1/audio/") else 2 * 1024 * 1024
            if size > max_size:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body is too large.", "request_id": request_id},
                    headers={"X-Request-ID": request_id},
                )
        except ValueError:
            pass

    # Protect credential endpoints from trivial brute force.
    if (
        settings.app_env.lower() in {"production", "demo"}
        and request.url.path in {"/api/developer/login", "/api/developer/register"}
    ):
        limit = settings.ednai_login_rate_limit_per_minute
        ok, retry = rate_limiter.check(
            f"auth:{client_ip(request)}:{request.url.path}",
            limit,
            60,
        )
        if not ok:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many authentication attempts.", "request_id": request_id},
                headers={"Retry-After": str(retry), "X-Request-ID": request_id},
            )

    # CSRF defense for cookie-authenticated state changes.
    if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"} and request.cookies.get("ednai_session"):
        origin = request.headers.get("origin")
        if origin and origin not in settings.allowed_origin_set:
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-site request rejected.", "request_id": request_id},
                headers={"X-Request-ID": request_id},
            )

    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    if (
        request.url.path.startswith("/api/developer/")
        or request.url.path.startswith("/v1/")
        or request.url.path.startswith("/api/studio/")
    ):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    if "server" in response.headers:
        del response.headers["server"]
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "media-src 'self' blob:; "
        "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    )
    if settings.app_env.lower() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    logger.info(
        "request_complete method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
        request_id,
    )
    return response
