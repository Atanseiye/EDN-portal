"""PostgreSQL byte stream over Cloudflare's supported TCP and verified TLS API."""
from struct import pack


class WorkerSocket:
    def __init__(self, host, port):
        from workers import import_from_javascript
        from pyodide.ffi import run_sync, to_js
        from js import Object
        self._wait = run_sync
        self._to_js = to_js
        options = lambda value: to_js(value, dict_converter=Object.fromEntries)
        self._socket = import_from_javascript("cloudflare:sockets").connect(
            options({"hostname": host, "port": port}), options({"secureTransport": "starttls"}))
        self._buffer = bytearray()
        self._open_streams()
        try:
            self.write(pack("!ii", 8, 80877103))
            if self.read(1) != b"S":
                raise ConnectionError("PostgreSQL server refused TLS")
            self._reader.releaseLock()
            self._writer.releaseLock()
            # Cloudflare verifies TLS against the original connection hostname.
            self._socket = self._socket.startTls()
            self._wait(self._socket.opened)
            self._open_streams()
        except BaseException:
            self.close()
            raise

    def _open_streams(self):
        self._reader = self._socket.readable.getReader()
        self._writer = self._socket.writable.getWriter()

    def makefile(self, mode):
        return self

    def read(self, size):
        while len(self._buffer) < size:
            result = self._wait(self._reader.read())
            if result.done:
                break
            self._buffer.extend(bytes(result.value.to_py()))
        data = bytes(self._buffer[:size])
        del self._buffer[:size]
        return data

    def write(self, data):
        self._wait(self._writer.write(self._to_js(bytes(data))))
        return len(data)

    def flush(self):
        pass

    def close(self):
        self._wait(self._socket.close())
