"""OAuth transport is mocked; no NASA credentials or real login are used."""
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from app.main import app
from app import earthdata_auth as auth

CLIENT_ID = 'TEST_ONLY_APP'
CLIENT_SECRET = 'TEST_ONLY_SECRET'
REDIRECT = 'http://127.0.0.1:3000/api/auth/earthdata/callback'


def configured(monkeypatch):
    # Existing transport fixtures are intentionally memory-only, never the user's store.
    monkeypatch.setenv('EARTHDATA_PERSIST_SESSIONS', '0')
    monkeypatch.setenv('EARTHDATA_CLIENT_ID', CLIENT_ID)
    monkeypatch.setenv('EARTHDATA_CLIENT_SECRET', CLIENT_SECRET)
    monkeypatch.setenv('EARTHDATA_REDIRECT_URI', REDIRECT)
    auth._pending.clear()
    auth._sessions.clear()
    auth._revoked_sessions.clear()
    monkeypatch.setattr(auth, '_revocation_overflow', False)


def begin(client):
    response = client.get('/auth/earthdata/start', follow_redirects=False)
    assert response.status_code == 302
    parsed = urlsplit(response.headers['location'])
    assert parsed.scheme == 'https' and parsed.hostname == 'urs.earthdata.nasa.gov'
    query = parse_qs(parsed.query)
    assert query['client_id'] == [CLIENT_ID] and query['redirect_uri'] == [REDIRECT]
    state = query['state'][0]
    assert response.cookies[auth.STATE_COOKIE] == state
    assert 'HttpOnly' in response.headers['set-cookie']
    return state


def test_unconfigured_is_not_connected(monkeypatch):
    for name in ('EARTHDATA_CLIENT_ID', 'EARTHDATA_CLIENT_SECRET', 'EARTHDATA_REDIRECT_URI'):
        monkeypatch.delenv(name, raising=False)
    client = TestClient(app)
    assert client.get('/auth/earthdata/status').json()['configured'] is False
    response = client.get('/auth/earthdata/start', follow_redirects=False)
    assert response.status_code == 503 and 'location' not in response.headers


def test_invalid_redirect_configuration_fails_closed(monkeypatch):
    configured(monkeypatch)
    monkeypatch.setenv('EARTHDATA_REDIRECT_URI', 'http://example.org/api/auth/earthdata/callback')
    client = TestClient(app)
    assert client.get('/auth/earthdata/status').json()['configured'] is False
    monkeypatch.setenv('EARTHDATA_REDIRECT_URI', 'https://example.org/other')
    assert auth.settings() is None


def test_account_connection_is_per_browser_and_one_time(monkeypatch):
    configured(monkeypatch)
    exchanges = []

    async def fake_exchange(config, code):
        exchanges.append(code)
        return auth.Grant('TEST_ONLY_USER_A_TOKEN',900)

    monkeypatch.setattr(auth, 'exchange_code', fake_exchange)
    first, second = TestClient(app), TestClient(app)
    state = begin(first)
    bad = second.get('/auth/earthdata/callback', params={'state': state, 'code': 'TEST_ONLY_CODE'},
                     follow_redirects=False)
    assert bad.headers['location'] == '/?earthdata=invalid_state'
    assert not exchanges
    callback = first.get('/auth/earthdata/callback', params={'state': state, 'code': 'TEST_ONLY_CODE'},
                         headers={'Cookie': f'{auth.STATE_COOKIE}={state}'}, follow_redirects=False)
    assert callback.status_code == 303 and callback.headers['location'] == '/?earthdata=connected'
    assert 'TEST_ONLY_USER_A_TOKEN' not in str(callback.headers)
    sid = callback.cookies[auth.SESSION_COOKIE]
    own = first.get('/auth/earthdata/status', headers={'Cookie': f'{auth.SESSION_COOKIE}={sid}'})
    assert own.json()['connected'] is True
    assert second.get('/auth/earthdata/status').json()['connected'] is False
    repeat = first.get('/auth/earthdata/callback', params={'state': state, 'code': 'TEST_ONLY_CODE'},
                       headers={'Cookie': f'{auth.STATE_COOKIE}={state}'}, follow_redirects=False)
    assert repeat.headers['location'] == '/?earthdata=invalid_state' and exchanges == ['TEST_ONLY_CODE']
    assert first.post('/auth/earthdata/logout', headers={'Cookie': f'{auth.SESSION_COOKIE}={sid}'}).status_code == 403
    logout = first.post('/auth/earthdata/logout',
                        headers={'Cookie': f'{auth.SESSION_COOKIE}={sid}', 'Origin': 'http://127.0.0.1:3000'})
    assert logout.status_code == 200
    assert first.get('/auth/earthdata/status', headers={'Cookie': f'{auth.SESSION_COOKIE}={sid}'}).json()['connected'] is False


def test_denied_and_exchange_failure_never_connect(monkeypatch):
    configured(monkeypatch)
    client = TestClient(app)
    state = begin(client)
    denied = client.get('/auth/earthdata/callback', params={'state': state, 'error': 'access_denied'},
                        headers={'Cookie': f'{auth.STATE_COOKIE}={state}'}, follow_redirects=False)
    assert denied.headers['location'] == '/?earthdata=denied'
    state = begin(client)
    async def bad_exchange(_config, _code):
        raise ValueError('TEST_ONLY_UPSTREAM_SECRET')
    monkeypatch.setattr(auth, 'exchange_code', bad_exchange)
    failed = client.get('/auth/earthdata/callback', params={'state': state, 'code': 'TEST_ONLY_CODE'},
                        headers={'Cookie': f'{auth.STATE_COOKIE}={state}'}, follow_redirects=False)
    assert failed.headers['location'] == '/?earthdata=failed'
    assert 'TEST_ONLY_UPSTREAM_SECRET' not in str(failed.headers)
    assert client.get('/auth/earthdata/status').json()['connected'] is False
