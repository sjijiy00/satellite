"""Fake OAuth grants only. Windows tests use real user-scope DPAPI, never NASA login."""
import asyncio
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import sys
import time

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app import earthdata_auth as auth, earthdata_store as storage
from app.main import app
from test_earthdata_auth import configured, begin

SID = 'TEST_ONLY_BROWSER_SESSION'
ACCESS = 'TEST_ONLY_ACCESS_TOKEN_NOT_REAL'
REFRESH = 'TEST_ONLY_REFRESH_TOKEN_NOT_REAL'


@pytest.fixture
def tmp_path():
    # Python 3.13's pytest mode=0700 temp directories are unreadable to this
    # restricted Windows token. Use an inherited-ACL, repository-local test folder.
    root = Path(__file__).resolve().parents[1] / '.private'
    root.mkdir(exist_ok=True)
    path = root / ('auth-test-' + secrets.token_hex(8))
    path.mkdir()
    yield path
    assert path.resolve().parent == root.resolve()
    shutil.rmtree(path)


def request(sid=SID):
    return Request({'type': 'http', 'headers': [(b'cookie', f'{auth.SESSION_COOKIE}={sid}'.encode()),
        (b'origin', b'http://127.0.0.1:3000')]})


@pytest.fixture
def persistence(monkeypatch, tmp_path):
    configured(monkeypatch)
    monkeypatch.setenv('EARTHDATA_PERSIST_SESSIONS', '1')
    monkeypatch.setattr(storage, 'STORE_PATH', tmp_path / 'private' / 'sessions.sqlite3')
    monkeypatch.setattr(auth, '_store_instance', None)
    monkeypatch.setattr(auth, '_store_identity', None)
    yield
    auth._sessions.clear()
    auth._pending.clear()


@pytest.fixture
def real_dpapi(persistence, monkeypatch):
    """Real encryption, explicitly mocked ACL installation; no user grant data."""
    if os.name != 'nt':
        pytest.skip('Real DPAPI requires Windows; no fake success on other platforms')
    # Storage lifecycle/crypto tests run independently of WRITE_DAC capability.
    # The unmocked ACL readiness test below records that capability separately.
    monkeypatch.setattr(storage, '_restrict_directory', lambda *_: None)
    store = auth._store(auth.settings())
    assert store.ready, 'Actual Windows DPAPI/storage preparation failed'
    return store


def test_windows_store_readiness_with_unmocked_acl(persistence, tmp_path):
    if os.name != 'nt':
        pytest.skip('Windows-only ACL and DPAPI readiness')
    directory = tmp_path / 'acl-probe'
    directory.mkdir()
    try:
        storage._restrict_directory(directory)
    except storage.StorageError:
        pytest.skip('Current execution token cannot install private Windows ACL (WRITE_DAC)')
    assert auth._store(auth.settings()).ready


def insert_session(lifetime=900, refresh=REFRESH, duration=3600):
    now, epoch = time.monotonic(), time.time()
    session = auth.Session(auth.Grant(ACCESS, 900, refresh), now+lifetime, now+duration,
        epoch_expires_at=epoch+lifetime, epoch_deadline=epoch+duration,
        fingerprint=auth._fingerprint(auth.settings()))
    auth._save(SID, session, auth.settings())
    auth._sessions[SID] = session
    return session


def test_windows_default_disabled_and_unavailable_are_distinct(persistence, monkeypatch):
    monkeypatch.delenv('EARTHDATA_PERSIST_SESSIONS')
    assert auth._persistence_enabled() is False
    assert json.loads(auth.status(request()).body)['storage'] == 'local_single_process_memory'
    monkeypatch.setenv('EARTHDATA_PERSIST_SESSIONS', '0')
    response = json.loads(auth.status(request()).body)
    assert response['storage'] == 'local_single_process_memory'
    assert not response['persistence_enabled'] and not response['persistence_ready']
    assert not storage.STORE_PATH.exists()
    monkeypatch.setenv('EARTHDATA_PERSIST_SESSIONS', '1')
    monkeypatch.setattr(storage, 'protect', lambda *_: (_ for _ in ()).throw(storage.StorageError()))
    response = json.loads(auth.status(request()).body)
    assert response['storage_error'] and not response['connected'] and not response['persistence_ready']
    assert auth.start().status_code == 503


def test_actual_dpapi_ciphertext_and_fresh_process_restoration(real_dpapi):
    insert_session()
    disk = storage.STORE_PATH.read_bytes()
    assert all(value.encode() not in disk for value in (SID, ACCESS, REFRESH))
    with closing(sqlite3.connect(storage.STORE_PATH, isolation_level=None)) as database:
        key, ciphertext = database.execute('SELECT sid_hash,payload FROM grants').fetchone()
    assert key == storage.session_key(SID) and ciphertext != ACCESS.encode()
    assert REFRESH.encode() not in ciphertext
    # A genuinely new interpreter, with an independent auth module/session cache.
    script = '''import json, sys
from pathlib import Path
from fastapi import Request
from app import earthdata_auth as auth, earthdata_store as storage
data=json.load(sys.stdin)
storage.STORE_PATH=Path(data['path'])
# Only ACL installation is mocked, exactly as in the parent test fixture.
storage._restrict_directory=lambda *_: None
req=Request({'type':'http','headers':[(b'cookie',(auth.SESSION_COOKIE+'='+data['sid']).encode())]})
sid, session=auth._session(req)
print(json.dumps({'restored': bool(session and session.grant.access_token==data['expected']),
 'separate_browser': auth._session(Request({'type':'http','headers':[]}))[1] is None,
 'expiry': bool(session and session.epoch_deadline > __import__('time').time())}))'''
    result = subprocess.run([sys.executable, '-c', script], input=json.dumps({
        'path': str(storage.STORE_PATH), 'sid': SID, 'expected': ACCESS}),
        capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, 'Fresh interpreter restoration failed'
    assert json.loads(result.stdout) == {'restored': True, 'separate_browser': True, 'expiry': True}
    auth._sessions.clear()
    restored = auth._session(request())[1]
    assert restored and restored.grant.refresh_token == REFRESH
    assert ACCESS not in repr(restored) and REFRESH not in repr(restored.grant)
    assert 'TEST_ONLY_SECRET' not in repr(auth.settings())


@pytest.mark.parametrize('failure', ['corrupt', 'other_user', 'configuration'])
def test_corruption_failed_unprotect_and_changed_configuration_fail_closed(real_dpapi, monkeypatch, failure):
    insert_session()
    auth._sessions.clear()
    if failure == 'corrupt':
        with closing(sqlite3.connect(storage.STORE_PATH, isolation_level=None)) as database:
            database.execute('UPDATE grants SET payload = ?', (b'NOT_DPAPI',))
    elif failure == 'other_user':
        # Failure injection represents another user's DPAPI failure, not an actual second OS login.
        def other_user(*_):
            raise storage.StorageError('TEST_ONLY_OTHER_OS_USER_OR_LOST_KEY')
        monkeypatch.setattr(storage, 'unprotect', other_user)
    else:
        monkeypatch.setenv('EARTHDATA_CLIENT_SECRET', 'TEST_ONLY_ROTATED_APP_SECRET')
    assert auth._session(request())[1] is None
    if failure == 'configuration':
        with closing(sqlite3.connect(storage.STORE_PATH, isolation_level=None)) as database:
            assert database.execute('SELECT count(*) FROM grants').fetchone()[0] == 1
        assert json.loads(auth.status(request()).body)['storage_isolation_required']
        monkeypatch.setenv('EARTHDATA_PERSIST_SESSIONS', '0')
        response = auth.logout(request())
        assert response.status_code == 503 and not json.loads(response.body)['storage_disposed']
        assert 'set-cookie' not in response.headers


@pytest.mark.parametrize('failure', ['row_deadline', 'epoch_deadline', 'access_without_refresh'])
def test_expired_session_and_access_without_refresh_never_restore(real_dpapi, failure):
    if failure == 'access_without_refresh':
        insert_session(lifetime=-1, refresh=None)
        auth._sessions.clear()
    else:
        session = insert_session()
        if failure == 'row_deadline':
            with closing(sqlite3.connect(storage.STORE_PATH, isolation_level=None)) as database:
                database.execute('UPDATE grants SET deadline = ?', (time.time()-1,))
            auth._sessions.clear()
        else:
            session.epoch_deadline = time.time()-1
    assert auth._session(request())[1] is None


def test_logout_deletes_disk_even_after_persistence_switch_disabled(real_dpapi, monkeypatch):
    insert_session()
    monkeypatch.setenv('EARTHDATA_PERSIST_SESSIONS', '0')
    assert auth.logout(request()).status_code == 200
    monkeypatch.setenv('EARTHDATA_PERSIST_SESSIONS', '1')
    assert auth._session(request())[1] is None
    with closing(sqlite3.connect(storage.STORE_PATH, isolation_level=None)) as database:
        assert database.execute('SELECT count(*) FROM grants').fetchone()[0] == 0


def test_logout_during_refresh_never_recreates_disk(real_dpapi, monkeypatch):
    insert_session(lifetime=-1)
    async def run():
        entered, resume = asyncio.Event(), asyncio.Event()
        async def refresh(*_):
            entered.set()
            await resume.wait()
            return auth.Grant('TEST_ONLY_ROTATED_ACCESS', 900, 'TEST_ONLY_ROTATED_REFRESH')
        monkeypatch.setattr(auth, 'exchange_refresh', refresh)
        task = asyncio.create_task(auth.access_token(request()))
        await entered.wait()
        assert auth.logout(request()).status_code == 200
        resume.set()
        with pytest.raises(auth.AuthenticationRequired):
            await task
    asyncio.run(run())
    auth._sessions.clear()
    assert auth._session(request())[1] is None


def test_refresh_rotation_persists_and_storage_failure_never_connects(real_dpapi, monkeypatch):
    insert_session(lifetime=-1)
    calls = []
    async def refresh(*_):
        calls.append(1)
        await asyncio.sleep(0)
        return auth.Grant('TEST_ONLY_ROTATED_ACCESS', 900, 'TEST_ONLY_ROTATED_REFRESH')
    monkeypatch.setattr(auth, 'exchange_refresh', refresh)
    async def run():
        assert await asyncio.gather(auth.access_token(request()), auth.access_token(request())) == [
            'TEST_ONLY_ROTATED_ACCESS'] * 2
    asyncio.run(run())
    assert len(calls) == 1
    auth._sessions.clear()
    restored = auth._session(request())[1]
    assert restored.grant.refresh_token == 'TEST_ONLY_ROTATED_REFRESH'
    restored.expires_at = 0
    def write_failure(*_):
        raise storage.StorageError('TEST_ONLY_SECRET_STORAGE_FAILURE')
    monkeypatch.setattr(real_dpapi, 'save', write_failure)
    with pytest.raises(auth.AuthenticationRequired):
        asyncio.run(auth.access_token(request()))
    auth._sessions.clear()
    assert auth._session(request())[1] is None


def test_callback_persistence_failure_never_sets_connected_cookie(real_dpapi, monkeypatch):
    async def exchange(*_):
        return auth.Grant(ACCESS, 900, REFRESH)
    monkeypatch.setattr(auth, 'exchange_code', exchange)
    client = TestClient(app)
    state = begin(client)
    def failed(*_):
        raise storage.StorageError('TEST_ONLY_STORAGE_ERROR')
    monkeypatch.setattr(real_dpapi, 'save', failed)
    response = client.get('/auth/earthdata/callback', params={'state': state, 'code': 'TEST_ONLY_CODE'},
        headers={'Cookie': f'{auth.STATE_COOKIE}={state}'}, follow_redirects=False)
    assert response.headers['location'] == '/?earthdata=failed'
    assert auth.SESSION_COOKIE not in response.cookies and not auth._sessions
    assert ACCESS not in str(response.headers)


def test_oauth_callback_saves_browser_grant_with_bounded_cookie(real_dpapi, monkeypatch):
    async def exchange(*_):
        return auth.Grant(ACCESS, 900, REFRESH)
    monkeypatch.setattr(auth, 'exchange_code', exchange)
    client = TestClient(app)
    state = begin(client)
    response = client.get('/auth/earthdata/callback', params={'state': state, 'code': 'TEST_ONLY_CODE'},
        headers={'Cookie': f'{auth.STATE_COOKIE}={state}'}, follow_redirects=False)
    assert response.headers['location'] == '/?earthdata=connected'
    sid = response.cookies[auth.SESSION_COOKIE]
    assert 'Max-Age=2592000' in response.headers['set-cookie']
    assert 'HttpOnly' in response.headers['set-cookie'] and 'SameSite=lax' in response.headers['set-cookie']
    auth._sessions.clear()
    restored = auth._session(request(sid))[1]
    assert restored and restored.grant.access_token == ACCESS
    assert json.loads(auth.status(request(sid)).body)['connection_expires_at'] <= time.time()+30*86400
    assert not TestClient(app).get('/auth/earthdata/status').json()['connected']


def test_ciphertext_cannot_move_between_browser_rows(real_dpapi):
    insert_session()
    with closing(sqlite3.connect(storage.STORE_PATH, isolation_level=None)) as database:
        database.execute('UPDATE grants SET sid_hash = ?', (storage.session_key('TEST_ONLY_OTHER_BROWSER'),))
    assert real_dpapi.load('TEST_ONLY_OTHER_BROWSER') is None
    assert real_dpapi.load(SID) is None


def test_refresh_refusal_disposes_disk_and_is_not_retried(real_dpapi, monkeypatch):
    insert_session(lifetime=-1)
    calls = []
    async def denied(*_):
        calls.append(1)
        raise ValueError('TEST_ONLY_REFUSAL_DETAIL')
    monkeypatch.setattr(auth, 'exchange_refresh', denied)
    with pytest.raises(auth.AuthenticationRequired):
        asyncio.run(auth.access_token(request()))
    with pytest.raises(auth.AuthenticationRequired):
        asyncio.run(auth.access_token(request()))
    assert len(calls) == 1
    auth._sessions.clear()
    assert auth._session(request())[1] is None


def test_limits_and_prune_with_real_ciphertext(real_dpapi, monkeypatch):
    insert_session()
    monkeypatch.setattr(storage, 'MAX_SESSIONS', 1)
    payload = real_dpapi.load(SID)
    with pytest.raises(storage.StorageError):
        real_dpapi.save('TEST_ONLY_SECOND_BROWSER', payload)
    assert not real_dpapi.ready
    real_dpapi.ready = True
    with closing(sqlite3.connect(storage.STORE_PATH, isolation_level=None)) as database:
        database.execute('UPDATE grants SET deadline = ?', (time.time()-1,))
    real_dpapi.save('TEST_ONLY_SECOND_BROWSER', payload)
    assert real_dpapi.load(SID) is None
    with pytest.raises(storage.StorageError):
        real_dpapi.save(SID, payload | {'deadline': time.time()+31*86400})


def test_provider_status_has_safe_fixed_shape_and_no_false_usgs_cdse_connection(monkeypatch):
    configured(monkeypatch)
    response = TestClient(app).get('/auth/providers/status')
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    providers = response.json()['providers']
    assert [p['provider_id'] for p in providers] == ['earth-search', 'copernicus', 'nasa-cmr']
    for provider in providers:
        assert set(provider) == {'provider_id', 'configured', 'connected', 'integration', 'storage', 'message'}
        assert not provider['connected']
    assert 'TEST_ONLY_SECRET' not in response.text and ACCESS not in response.text


def test_mocked_dpapi_failure_and_oversize_database_are_not_reported_ready(persistence, monkeypatch, tmp_path):
    # Portable failure-path test. It does not claim successful DPAPI encryption.
    monkeypatch.setattr(storage, '_restrict_directory', lambda *_: None)
    monkeypatch.setattr(storage, 'protect', lambda *_: (_ for _ in ()).throw(storage.StorageError()))
    assert not storage.GrantStore(tmp_path/'failed.sqlite3', 'TEST_ONLY_FP').ready
    monkeypatch.setattr(storage, 'protect', lambda data, _: data)
    monkeypatch.setattr(storage, 'unprotect', lambda data, _: data)
    path = tmp_path/'oversize.sqlite3'
    with path.open('wb') as file:
        file.truncate(storage.MAX_DATABASE_BYTES+1)
    assert not storage.GrantStore(path, 'TEST_ONLY_FP').ready


def fresh_process_connection():
    """New interpreter and real DPAPI; fake grants and explicitly mocked ACL installer."""
    script = '''import json, sys
from pathlib import Path
from fastapi import Request
from app import earthdata_auth as auth, earthdata_store as storage
data=json.load(sys.stdin)
storage.STORE_PATH=Path(data['path'])
storage._restrict_directory=lambda *_: None
req=Request({'type':'http','headers':[(b'cookie',(auth.SESSION_COOKIE+'='+data['sid']).encode())]})
print(json.dumps({'connected':json.loads(auth.status(req).body)['connected']}))'''
    result = subprocess.run([sys.executable, '-c', script], input=json.dumps({
        'path': str(storage.STORE_PATH), 'sid': SID}), capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, 'Fresh interpreter check failed'
    return json.loads(result.stdout)['connected']


def test_journal_survives_db_delete_failure_and_restart_rejects_copied_sid(real_dpapi, monkeypatch):
    insert_session()
    original_delete = real_dpapi._delete_grant
    def failed_delete(*_):
        raise sqlite3.OperationalError('TEST_ONLY_DB_DELETE_FAILURE')
    monkeypatch.setattr(real_dpapi, '_delete_grant', failed_delete)
    response = auth.logout(request())
    result = json.loads(response.body)
    assert response.status_code == 503 and result['storage_disposed'] is False
    assert result['revocation_recorded'] is True and result['cleanup_required'] is True
    assert 'set-cookie' not in response.headers
    assert auth._session(request())[1] is None
    with closing(sqlite3.connect(storage.STORE_PATH)) as database:
        assert database.execute('SELECT count(*) FROM grants').fetchone()[0] == 1
    assert not fresh_process_connection()
    journal = real_dpapi._read_journal()
    assert time.time() < journal[storage.session_key(SID)] <= time.time()+30*86400
    disk = real_dpapi.journal_path.read_bytes()
    assert all(value.encode() not in disk for value in (SID, ACCESS, REFRESH))
    monkeypatch.setattr(real_dpapi, '_delete_grant', original_delete)
    repaired = auth.logout(request())
    assert repaired.status_code == 200 and json.loads(repaired.body)['storage_disposed']
    assert json.loads(repaired.body)['revocation_recorded']
    assert not fresh_process_connection()


def test_all_persistent_writes_fail_cookie_kept_and_retry_after_repair(real_dpapi, monkeypatch):
    insert_session()
    with monkeypatch.context() as broken:
        def denied(*_):
            raise PermissionError('TEST_ONLY_ALL_DURABLE_WRITES_DENIED')
        broken.setattr(storage, '_atomic_write', denied)
        deletes = []
        broken.setattr(real_dpapi, '_delete_grant', lambda *_: deletes.append(1))
        response = auth.logout(request())
        result = json.loads(response.body)
        assert response.status_code == 503 and not result['storage_disposed']
        assert not result['revocation_recorded'] and not deletes
        assert '영구 폐기는 보장할 수 없습니다' in result['message']
        assert 'set-cookie' not in response.headers
        assert auth._session(request())[1] is None
        with pytest.raises(auth.AuthenticationRequired):
            asyncio.run(auth.access_token(request()))
        # With NO durable write possible, another process can still restore the old grant.
        # This proves the limitation; it is not reported as successful durable revocation.
        assert fresh_process_connection()
    repaired = auth.logout(request())
    assert repaired.status_code == 200 and json.loads(repaired.body)['storage_disposed']
    assert 'Max-Age=0' in repaired.headers['set-cookie']
    assert not fresh_process_connection()


def test_missing_cookie_cannot_report_original_disposal_success(real_dpapi):
    insert_session()
    response = auth.logout(request(''))
    assert response.status_code == 503
    assert json.loads(response.body)['storage_disposed'] is False
    assert 'set-cookie' not in response.headers
    assert real_dpapi.load(SID) is not None


@pytest.mark.parametrize('disabled', [None, '', '0', 'true', '2'])
def test_only_explicit_one_enables_persistence(persistence, monkeypatch, disabled):
    if disabled is None:
        monkeypatch.delenv('EARTHDATA_PERSIST_SESSIONS')
    else:
        monkeypatch.setenv('EARTHDATA_PERSIST_SESSIONS', disabled)
    assert not auth._persistence_enabled()
    assert not json.loads(auth.status(request()).body)['persistence_enabled']
    assert not storage.STORE_PATH.exists()
    assert auth._store(auth.settings()) is None


def test_v2_optin_and_reenable_never_restore_while_disabled(real_dpapi, monkeypatch):
    insert_session()
    with closing(sqlite3.connect(storage.STORE_PATH)) as database:
        assert database.execute('PRAGMA user_version').fetchone()[0] == storage.STORE_VERSION == 2
        assert database.execute('SELECT version FROM metadata').fetchone()[0] == 2
    monkeypatch.setenv('EARTHDATA_PERSIST_SESSIONS', '0')
    # Disabling also stops reuse of an already cached persistent grant.
    assert auth._session(request())[1] is None
    assert real_dpapi.load(SID) is not None  # Disabled means no automatic cleanup or restoration.
    monkeypatch.setenv('EARTHDATA_PERSIST_SESSIONS', '1')
    assert auth._session(request())[1] is not None


@pytest.mark.parametrize('version', [0, 99])
def test_legacy_store_never_restores_migrates_or_deletes_on_reenable_or_logout(persistence, monkeypatch, version):
    storage.STORE_PATH.parent.mkdir()
    with closing(sqlite3.connect(storage.STORE_PATH, isolation_level=None)) as database:
        database.execute('CREATE TABLE grants (sid_hash TEXT PRIMARY KEY, payload BLOB, deadline REAL, fingerprint TEXT)')
        database.execute(f'PRAGMA user_version = {version}')
        database.execute('INSERT INTO grants VALUES (?, ?, ?, ?)',
            (storage.session_key(SID), b'TEST_ONLY_LEGACY_ENCRYPTED_GRANT', time.time()+3600,
             auth._fingerprint(auth.settings())))
    before = storage.STORE_PATH.read_bytes()
    monkeypatch.setenv('EARTHDATA_PERSIST_SESSIONS', '0')
    assert auth._session(request())[1] is None
    assert not json.loads(auth.status(request()).body)['persistence_enabled']
    monkeypatch.setenv('EARTHDATA_PERSIST_SESSIONS', '1')
    result = json.loads(auth.status(request()).body)
    assert result['storage_isolation_required'] and not result['persistence_ready']
    assert result['storage_message'] == storage.ISOLATION_MESSAGE
    assert auth.start().status_code == 503 and auth._session(request())[1] is None
    monkeypatch.setenv('EARTHDATA_PERSIST_SESSIONS', '0')
    response = auth.logout(request())
    assert response.status_code == 503 and not json.loads(response.body)['storage_disposed']
    assert 'set-cookie' not in response.headers
    assert json.loads(response.body)['storage_isolation_required']
    assert storage.STORE_PATH.read_bytes() == before
    assert not storage.STORE_PATH.with_name(storage.STORE_PATH.name + '.revocations').exists()


@pytest.mark.parametrize('failure', ['tamper', 'missing', 'read_failure'])
def test_journal_tamper_or_unavailable_blocks_memory_load_save_and_restart(real_dpapi, monkeypatch, failure):
    session = insert_session()
    if failure == 'tamper':
        real_dpapi.journal_path.write_bytes(b'TEST_ONLY_TAMPERED_JOURNAL')
    elif failure == 'missing':
        real_dpapi.journal_path.unlink()
    else:
        def failed_read():
            raise PermissionError('TEST_ONLY_JOURNAL_READ_DENIED')
        monkeypatch.setattr(real_dpapi, '_read_journal', failed_read)
    assert auth._session(request())[1] is None
    with pytest.raises(storage.StorageError):
        real_dpapi.load(SID)
    with pytest.raises(storage.StorageError):
        auth._save(SID, session, auth.settings())
    if failure != 'read_failure':
        fresh = storage.GrantStore(storage.STORE_PATH, auth._fingerprint(auth.settings()))
        assert not fresh.ready


def test_revocation_count_and_file_count_are_bounded(real_dpapi, monkeypatch):
    insert_session()
    monkeypatch.setattr(storage, 'MAX_REVOCATIONS', 0)
    with pytest.raises(storage.StorageError) as error:
        real_dpapi.delete(SID)
    assert not error.value.revocation_recorded
    with closing(sqlite3.connect(storage.STORE_PATH)) as database:
        assert database.execute('SELECT count(*) FROM grants').fetchone()[0] == 1
    monkeypatch.setattr(storage, 'MAX_REVOCATIONS', 1000)
    for index in range(storage.MAX_STORE_FILES):
        (storage.STORE_PATH.parent / f'TEST_ONLY_ABANDONED_{index}.tmp').touch()
    with pytest.raises(storage.StorageError):
        real_dpapi.is_revoked(SID)


def test_default_login_is_eight_hour_memory_only(persistence, monkeypatch):
    monkeypatch.delenv('EARTHDATA_PERSIST_SESSIONS')
    async def exchange(*_):
        return auth.Grant(ACCESS, 900, REFRESH)
    monkeypatch.setattr(auth, 'exchange_code', exchange)
    client = TestClient(app)
    state = begin(client)
    response = client.get('/auth/earthdata/callback', params={'state': state, 'code': 'TEST_ONLY_CODE'},
        headers={'Cookie': f'{auth.STATE_COOKIE}={state}'}, follow_redirects=False)
    assert response.headers['location'] == '/?earthdata=connected'
    assert 'Max-Age=28800' in response.headers['set-cookie']
    sid = response.cookies[auth.SESSION_COOKIE]
    result = json.loads(auth.status(request(sid)).body)
    assert result['connected'] and result['storage'] == 'local_single_process_memory'
    assert not result['persistence_enabled'] and result['connection_expires_at'] <= time.time()+8*3600
    assert not storage.STORE_PATH.exists()


def test_unconfigured_logout_cannot_claim_disk_disposal(real_dpapi, monkeypatch):
    insert_session()
    monkeypatch.delenv('EARTHDATA_CLIENT_SECRET')
    response = auth.logout(request())
    assert response.status_code == 403 and 'set-cookie' not in response.headers
    assert real_dpapi.load(SID) is not None
