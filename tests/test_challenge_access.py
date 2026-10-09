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


def test_postgres_session_loads_account_and_balance_in_one_transaction():
    import hashlib
    from unittest.mock import MagicMock
    from server.developer_store import DeveloperStore
    store = DeveloperStore.__new__(DeveloperStore)
    store.use_postgres = True
    store._postgres = MagicMock()
    connection = store._postgres.return_value.__enter__.return_value
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = ('demo-id', 'demo@edn.com', 'Demo', 'active', True, 'created', 123)
    store.account = MagicMock(side_effect=AssertionError('Extra connection required'))
    account = store.resolve_session('session-token')
    assert account['email'] == 'demo@edn.com' and account['is_demo'] is True
    assert account['balance_microusd'] == 123
    store._postgres.assert_called_once()
    query, parameters = cursor.execute.call_args.args
    assert parameters[0] == hashlib.sha256(b'session-token').hexdigest()
    assert 's.revoked_at IS NULL' in query and 's.expires_at>%s' in query
    cursor.fetchone.return_value = None
    assert store.resolve_session('expired-session') is None
