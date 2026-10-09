import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest

from server.postgres import connect
from ednai.providers import GradioSpaceProvider, ProviderError


def test_worker_database_transaction_commits_and_rolls_back(monkeypatch):
    monkeypatch.setenv("EDNAI_DATABASE_DRIVER", "pg8000")
    connection = MagicMock()
    dbapi = SimpleNamespace(connect=MagicMock(return_value=connection))
    monkeypatch.setitem(sys.modules, "pg8000", SimpleNamespace(dbapi=dbapi))
    monkeypatch.setitem(sys.modules, "pg8000.dbapi", dbapi)
    with connect("postgresql://user:password@example.com/db") as transaction:
        with transaction.cursor() as cursor:
            cursor.execute("SELECT 1")
    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()
    connection.close.assert_called_once()
    context = dbapi.connect.call_args.kwargs["ssl_context"]
    assert context.check_hostname is True
    assert context.verify_mode != 0
    connection.reset_mock()
    with pytest.raises(ValueError):
        with connect("postgresql://user:password@example.com/db"):
            raise ValueError("Abort transaction")
    connection.rollback.assert_called_once()
    connection.commit.assert_not_called()
    connection.close.assert_called_once()


def test_worker_gradio_http_preserves_provenance_and_exact_usage(monkeypatch):
    import ednai.gradio_http as adapter
    monkeypatch.setenv("EDNAI_WORKERS", "true")
    def handle(request):
        if request.url.host == "huggingface.co":
            return httpx.Response(200, json={"host": "https://test-runtime.hf.space"})
        if request.method == "POST":
            return httpx.Response(200, json={"event_id": "job"})
        return httpx.Response(200, text='event: complete\ndata: [{"model":"NCAIR1/N-ATLaS","text":"Hello", "usage":{"total_tokens":4}}]\n\n')
    client = httpx.Client(transport=httpx.MockTransport(handle))
    monkeypatch.setattr(adapter.httpx, "Client", lambda **kwargs: client)
    result = GradioSpaceProvider("test/runtime").generate([])
    assert result.text == "Hello"
    assert result.usage["total_tokens"] == 4


def test_worker_gradio_rejects_substituted_models(monkeypatch):
    import ednai.gradio_http as adapter
    monkeypatch.setenv("EDNAI_WORKERS", "true")
    monkeypatch.setattr(adapter, "predict", lambda *args: {"model": "wrong/model", "text": "Hello"})
    with pytest.raises(ProviderError, match="provenance"):
        GradioSpaceProvider("test/runtime").generate([])
