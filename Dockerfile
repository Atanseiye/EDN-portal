FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

WORKDIR /app

COPY pyproject.toml README.md ./
COPY ednai ./ednai
COPY server ./server
COPY web ./web
COPY docs ./docs
COPY fine_tuning ./fine_tuning
COPY benchmarks ./benchmarks
COPY examples ./examples

RUN python -m pip install --no-cache-dir ".[server]" \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin ednai \
    && chown -R ednai:ednai /app

USER 10001:10001

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/live', timeout=3).read()" || exit 1

CMD ["sh", "-c", "exec uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --no-access-log"]
