"""Synchronous HTTPX transport backed by Cloudflare's asynchronous fetch API."""
import httpx


class WorkerHTTPTransport(httpx.BaseTransport):
    def handle_request(self, request):
        from js import fetch, Object, AbortSignal, Uint8Array
        from pyodide.ffi import run_sync, to_js
        options = {"method": request.method, "headers": dict(request.headers),
                   "signal": AbortSignal.timeout(240000)}
        if request.content:
            options["body"] = to_js(request.content)
        response = run_sync(fetch(str(request.url), to_js(options, dict_converter=Object.fromEntries)))
        body = bytes(Uint8Array.new(run_sync(response.arrayBuffer())).to_py())
        content_type = response.headers.get("content-type")
        return httpx.Response(response.status, content=body,
                              headers={"content-type": content_type} if content_type else {})
