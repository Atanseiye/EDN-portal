import functools
import inspect
import json
import os
import asyncio

from workers import WorkerEntrypoint

# Import framework code during isolate startup, outside the request CPU budget.
os.environ.update(EDNAI_WORKERS="true", EDNAI_DATABASE_DRIVER="pg8000", EDNAI_SKIP_DB_INIT="true")
import server.main as main
from server.config import Settings
from server.security import validate_production_settings
from server.billing import Pricing
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.routing import request_response
import ednai.gradio_http as gradio_http
from ednai.worker_http import WorkerHTTPTransport
gradio_http.worker_transport = WorkerHTTPTransport()

_app = main.app
_initialized = False
_lock = asyncio.Lock()

PAGES = {
    "/": "/index.html", "/developer": "/developer.html", "/challenge": "/challenge.html",
    "/guide": "/guide.html", "/guide/en": "/guide-en.html", "/guide/yo": "/guide-yo.html",
    "/guide/ha": "/guide-ha.html", "/guide/ig": "/guide-ig.html",
    "/brand/ednai-logo.png": "/ednai-logo.png",
}


def configure_password_hashing():
    # Preserve the existing password format; WebCrypto does PBKDF2 off the CPU budget.
    from js import crypto, Uint8Array, Object
    from pyodide.ffi import to_js, run_sync
    import secrets
    import hashlib
    import server.developer_store as store

    def pbkdf2_hmac(hash_name, password, salt, iterations, dklen=None):
        algorithms = {"sha1": ("SHA-1", 20), "sha256": ("SHA-256", 32),
                      "sha384": ("SHA-384", 48), "sha512": ("SHA-512", 64)}
        algorithm_name, default_length = algorithms[hash_name.lower()]
        key = run_sync(crypto.subtle.importKey("raw", to_js(bytes(password)), "PBKDF2", False, to_js(["deriveBits"])))
        algorithm = to_js({"name": "PBKDF2", "salt": to_js(bytes(salt)), "iterations": iterations,
                           "hash": algorithm_name}, dict_converter=Object.fromEntries)
        result = run_sync(crypto.subtle.deriveBits(algorithm, key, (dklen or default_length) * 8))
        return bytes(Uint8Array.new(result).to_py())

    # CPython's OpenSSL PBKDF2 is absent in Workers; SCRAM needs the same operation.
    hashlib.pbkdf2_hmac = pbkdf2_hmac

    def password_hash(password, salt_hex=None):
        salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
        return salt.hex(), pbkdf2_hmac("sha256", password.encode(), salt, 310000).hex()
    store._password_hash = password_hash


configure_password_hashing()
async def run_inline(function, *args, **kwargs):
    return function(*args, **kwargs)
main.run_in_threadpool = run_inline
for route in _app.routes:
    if hasattr(route, "dependant") and not inspect.iscoroutinefunction(route.dependant.call):
        def wrap(function):
            @functools.wraps(function)
            async def call(**kwargs):
                return function(**kwargs)
            return call
        route.dependant.call = wrap(route.dependant.call)
        route.app = request_response(route.get_route_handler())


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        global _initialized
        if not _initialized:
            async with _lock:
                if not _initialized:
                    config = json.loads(self.env.EDNAI_CONFIG)
                    main.settings = Settings(**{key.lower(): value for key, value in config.items()})
                    validate_production_settings(main.settings)
                    main.store.database_url = main.settings.ednai_database_url
                    main.store.use_postgres = True
                    main.developer_store.database_url = main.settings.ednai_database_url
                    main.developer_store.use_postgres = True
                    main.provider = main.build_provider()
                    main.pricing = Pricing.from_values(main.settings.ednai_input_usd_per_1m_tokens,
                                                       main.settings.ednai_output_usd_per_1m_tokens)
                    _app.user_middleware = [m for m in _app.user_middleware if m.cls not in (TrustedHostMiddleware, CORSMiddleware)]
                    _app.add_middleware(TrustedHostMiddleware, allowed_hosts=main.settings.trusted_host_list)
                    _app.add_middleware(CORSMiddleware, allow_origins=main.settings.cors_origin_list,
                        allow_credentials=True, allow_methods=["GET", "POST", "DELETE", "HEAD", "OPTIONS"],
                        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
                        expose_headers=["Retry-After", "X-ZeroGPU-Resets-At"])
                    _initialized = True
        from urllib.parse import urlsplit
        url = urlsplit(request.url)
        path = url.path
        if path in PAGES or path.startswith("/assets/"):
            from js import Request
            asset_path = PAGES.get(path, path.removeprefix("/assets"))
            asset_url = f"{url.scheme}://{url.netloc}{asset_path}"
            response = await self.env.ASSETS.fetch(Request.new(asset_url, request.js_object))
            return response
        import asgi
        return await asgi.fetch(_app, request.js_object, self.env)
