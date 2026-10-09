import pytest
from fastapi.testclient import TestClient
import server.main as main


@pytest.mark.parametrize('account,status', [
    (None, 401),
    ({'email': 'builder@example.com', 'is_demo': False}, 403),
    ({'email': 'demo@edn.com', 'is_demo': False}, 403),
    ({'email': 'other@example.com', 'is_demo': True}, 403),
    ({'email': 'demo@edn.com', 'is_demo': True}, 200),
])
def test_challenge_requires_the_exact_demo_session(monkeypatch, account, status):
    monkeypatch.setattr(main.developer_store, 'resolve_session', lambda token: account)
    with TestClient(main.app) as client:
        client.cookies.set('ednai_session', 'test-session')
        for path in ['/challenge', '/assets/challenge.html', '/assets/%63hallenge.html', '/api/challenge/readiness']:
            response = client.get(path)
            assert response.status_code == status
            assert response.headers['cache-control'] == 'private, no-store'


def test_challenge_cannot_bypass_disabled_auth(monkeypatch):
    monkeypatch.setattr(main.settings, 'ednai_auth_enabled', False)
    with TestClient(main.app) as client:
        assert client.get('/api/challenge/readiness').status_code == 503
        assert client.get('/challenge').status_code == 503
