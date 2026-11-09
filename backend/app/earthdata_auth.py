"""Local single-process Earthdata OAuth bridge. No user token is exposed to the browser."""
import asyncio
import hmac
import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from threading import Lock
from urllib.parse import urlencode, urlsplit

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from . import earthdata_store

EARTHDATA_ORIGIN = 'https://urs.earthdata.nasa.gov'
CALLBACK_PATH = '/api/auth/earthdata/callback'
STATE_COOKIE = 'satellite_edl_state'
SESSION_COOKIE = 'satellite_edl_session'
FLOW_SECONDS = 300
MAX_SESSIONS = 1000
SESSION_SECONDS = 8 * 3600
PERSIST_SESSION_SECONDS = earthdata_store.MAX_SESSION_SECONDS
REFRESH_MARGIN = 60


@dataclass(frozen=True, repr=False)
class Settings:
    client_id: str
    client_secret: str
    redirect_uri: str
    origin: str
    secure_cookie: bool


def settings():
    client_id = os.getenv('EARTHDATA_CLIENT_ID', '').strip()
    client_secret = os.getenv('EARTHDATA_CLIENT_SECRET', '').strip()
    redirect_uri = os.getenv('EARTHDATA_REDIRECT_URI', '').strip()
    if not all((client_id, client_secret, redirect_uri)):
        return None
    try:
        parsed = urlsplit(redirect_uri)
        localhost = parsed.hostname in ('127.0.0.1', 'localhost')
        if (parsed.scheme != 'https' and not (parsed.scheme == 'http' and localhost)
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or not parsed.netloc or parsed.path != CALLBACK_PATH):
            return None
        # No public deployment of this local credential store. A shared encrypted
        # store and key management must be implemented before non-local OAuth is enabled.
        if not localhost:
            return None
        return Settings(client_id, client_secret, redirect_uri,
                        f'{parsed.scheme}://{parsed.netloc}', parsed.scheme == 'https')
    except ValueError:
        return None


# Only suitable for the repository's single-process local launcher. Public/multiworker
# deployment needs a shared, encrypted session store before OAuth is enabled there.
_pending: dict[str, float] = {}
@dataclass(frozen=True, repr=False)
class Grant:
    access_token: str
    lifetime: int
    refresh_token: str | None = None


@dataclass(repr=False)
class Session:
    grant: Grant
    expires_at: float
    deadline: float
    state: str = 'connected'
    refresh_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    epoch_expires_at: float | None = None
    epoch_deadline: float | None = None
    fingerprint: str | None = None
    persistent: bool = False


_sessions: dict[str, Session] = {}
_lock = Lock()
_store_instance = None
_store_identity = None
_store_lock = Lock()
_revoked_sessions: dict[str, float] = {}
_revocation_overflow = False


def _fingerprint(config):
    return hashlib.sha256(json.dumps([config.client_id, config.client_secret,
        config.redirect_uri], separators=(',', ':')).encode()).hexdigest()


def _persistence_enabled():
    return os.getenv('EARTHDATA_PERSIST_SESSIONS', '').strip() == '1'


def _store(config, *, for_disposal=False):
    global _store_instance, _store_identity
    if not _persistence_enabled() and not for_disposal:
        return None
    try:
        exists = (earthdata_store.STORE_PATH.exists() or
            earthdata_store.STORE_PATH.with_name(earthdata_store.STORE_PATH.name + '.revocations').exists())
        if for_disposal and not exists:
            return None
    except OSError:
        raise earthdata_store.StorageError('Earthdata storage unavailable') from None
    if not config or os.name != 'nt':
        if for_disposal and exists:
            raise earthdata_store.StorageError('Store isolation required')
        return None
    identity = (str(earthdata_store.STORE_PATH), _fingerprint(config))
    with _store_lock:
        if (_store_identity != identity or (for_disposal and _store_instance
                and not _store_instance.protection_ready and not _store_instance.isolation_required)):
            _store_identity = identity
            _store_instance = earthdata_store.GrantStore(*identity)
        return _store_instance


def _discard(sid, config):
    store = _store(config, for_disposal=True)
    if store:
        store.delete(sid)
        return True
    return False


def _block_session(sid):
    """Called with _lock held; deny reuse even when EVERY durable write fails."""
    global _revocation_overflow
    now = time.time()
    for key, deadline in list(_revoked_sessions.items()):
        if deadline <= now:
            _revoked_sessions.pop(key, None)
    key = earthdata_store.session_key(sid)
    if key not in _revoked_sessions and len(_revoked_sessions) >= MAX_SESSIONS:
        _revocation_overflow = True  # Fail closed for this process rather than evict a denial.
    else:
        _revoked_sessions[key] = now + PERSIST_SESSION_SECONDS


def _save(sid, session, config):
    if not _persistence_enabled():
        return
    store = _store(config)
    if not store or not store.ready:
        raise earthdata_store.StorageError('Earthdata storage unavailable')
    store.save(sid, {'access_token': session.grant.access_token,
        'refresh_token': session.grant.refresh_token, 'lifetime': session.grant.lifetime,
        'expires_at': session.epoch_expires_at, 'deadline': session.epoch_deadline})
    session.persistent = True


def _expired(session, now=None):
    return (session.deadline <= (time.monotonic() if now is None else now)
        or (session.epoch_deadline is not None and session.epoch_deadline <= time.time()))


def _prune(now):
    for key, expiry in list(_pending.items()):
        if expiry <= now:
            _pending.pop(key, None)
    for key, session in list(_sessions.items()):
        if _expired(session, now):
            _sessions.pop(key, None)
            try:
                _discard(key, settings())
            except earthdata_store.StorageError:
                pass


def _session(request):
    sid = request.cookies.get(SESSION_COOKIE)
    if sid and len(sid) > 256:
        return None, None
    config = settings()
    with _lock:
        _prune(time.monotonic())
        if (_revocation_overflow or (sid and
                _revoked_sessions.get(earthdata_store.session_key(sid), 0) > time.time())):
            return sid, None
        session = _sessions.get(sid) if sid else None
        if session and session.persistent and not _persistence_enabled():
            _sessions.pop(sid, None)
            session = None
        if session and session.fingerprint and (not config or session.fingerprint != _fingerprint(config)):
            _sessions.pop(sid, None)
            session = None
        store = _store(config)
        if _persistence_enabled() and config and (not store or not store.ready):
            return sid, None
        if sid and store:
            try:
                if store.is_revoked(sid):
                    _sessions.pop(sid, None)
                    return sid, None
            except earthdata_store.StorageError:
                return sid, None
        if sid and not session and store:
            try:
                payload = store.load(sid)
                if payload:
                    grant = parse_grant({'access_token': payload['access_token'],
                        'refresh_token': payload['refresh_token'], 'expires_in': payload['lifetime']})
                    if payload['expires_at'] <= time.time() and not grant.refresh_token:
                        store.delete(sid)
                    elif len(_sessions) < MAX_SESSIONS:
                        now, epoch = time.monotonic(), time.time()
                        session = Session(grant, now + payload['expires_at'] - epoch,
                            now + payload['deadline'] - epoch, epoch_expires_at=payload['expires_at'],
                            epoch_deadline=payload['deadline'], fingerprint=_fingerprint(config), persistent=True)
                        _sessions[sid] = session
            except (earthdata_store.StorageError, ValueError, KeyError, TypeError):
                # Never fall back to an unvalidated token when restoration fails.
                try:
                    store.delete(sid)
                except earthdata_store.StorageError:
                    pass
                session = None
        return sid, session


def require_reconnection(request):
    sid, session = _session(request)
    with _lock:
        if session:
            session.state = 'reconnection_required'
            session.grant = Grant('', 0)
        if sid:
            if _persistence_enabled():
                _block_session(sid)
            try:
                _discard(sid, settings())
            except earthdata_store.StorageError:
                pass


class AuthenticationRequired(Exception):
    pass


async def access_token(request, *, force_refresh=False, failed_token=None):
    """One refresh per session at a time; no retries after refusal/revocation."""
    config = settings()
    sid, session = _session(request)
    if not config or not session or session.state != 'connected':
        raise AuthenticationRequired()
    previous = failed_token if failed_token is not None else session.grant.access_token
    async with session.refresh_lock:
        if (_sessions.get(sid) is not session or session.state != 'connected'
                or _expired(session)):
            raise AuthenticationRequired()
        if (session.expires_at - time.monotonic() > min(REFRESH_MARGIN,session.grant.lifetime/10) and
                (not force_refresh or session.grant.access_token != previous)):
            return session.grant.access_token
        if not session.grant.refresh_token:
            if session.expires_at > time.monotonic() and not force_refresh:
                return session.grant.access_token
            require_reconnection(request)
            raise AuthenticationRequired()
        try:
            grant = await exchange_refresh(config, session.grant.refresh_token)
            # Logout during an in-flight refresh must not recreate a session.
            current_config = settings()
            if (_sessions.get(sid) is not session or session.state != 'connected'
                    or _expired(session) or not current_config
                    or _fingerprint(current_config) != _fingerprint(config)):
                raise AuthenticationRequired()
            with _lock:
                if _sessions.get(sid) is not session or session.state != 'connected':
                    raise AuthenticationRequired()
                # Save rotated refresh token before allowing another request to use it.
                session.grant = grant
                session.expires_at = time.monotonic() + grant.lifetime
                session.epoch_expires_at = time.time() + grant.lifetime
                _save(sid, session, config)
            return grant.access_token
        except (httpx.HTTPError, ValueError, asyncio.TimeoutError, earthdata_store.StorageError):
            # A failed persistent rotation must not leave the old grant restorable.
            session.state = 'reconnection_required'
            session.grant = Grant('', 0)
            try:
                _discard(sid, config)
            except earthdata_store.StorageError:
                pass
            require_reconnection(request)
            raise AuthenticationRequired() from None


def _no_store(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


def status(request: Request):
    from . import operator_access as operator
    if operator.enabled('nasa'):
        return _no_store(JSONResponse({**operator.public_status('nasa'),'refresh_available':False,'reauthorization_required':False}))
    config = settings()
    connected = False
    if config:
        _, session = _session(request)
        connected = bool(session and session.state == 'connected' and
                         (session.expires_at > time.monotonic() or session.grant.refresh_token))
    else:
        session = None
    enabled = _persistence_enabled()
    store = _store(config)
    ready = bool(store and store.ready)
    storage = ('local_single_process_windows_dpapi' if ready else
        'local_single_process_memory' if not enabled else 'local_persistence_unavailable')
    storage_message = ('Windows 현재 OS 사용자 DPAPI 암호화 저장입니다. 동시 서버 프로세스는 지원하지 않습니다.'
        if ready else '기본 메모리 모드(최대 8시간)입니다. 영속 저장은 EARTHDATA_PERSIST_SESSIONS=1 명시 설정에서만 사용하며 재시작하면 메모리 연결이 해제됩니다.' if not enabled else
        earthdata_store.ISOLATION_MESSAGE if store and store.isolation_required else
        '영속 저장을 준비하지 못했습니다. 앱 설정과 Windows 사용자 저장 권한을 확인하세요. 연결 유지 성공이 아닙니다.')
    sid = request.cookies.get(SESSION_COOKIE)
    blocked = (_revocation_overflow or bool(sid and len(sid) <= 256 and
        _revoked_sessions.get(earthdata_store.session_key(sid), 0) > time.time()))
    return _no_store(JSONResponse({'configured': bool(config), 'connected': connected,
        'reauthorization_required': bool(not connected and (session or blocked)),
        'refresh_available': bool(session and session.grant.refresh_token and connected),
        'storage': storage, 'persistence_enabled': enabled, 'persistence_ready': ready,
        'storage_format_version': earthdata_store.STORE_VERSION,
        'storage_isolation_required': bool(store and store.isolation_required),
        'storage_error': bool(enabled and config and not ready), 'storage_message': storage_message,
        'multi_process_supported': False,
        'connection_expires_at': (session.epoch_deadline if session and connected else None),
        'access_token_expires_at': (session.epoch_expires_at if session and connected else None),
        'scope': 'Earthdata 계정 연결 상태만 확인했습니다. 영상 파일 접근은 별도 검사해야 합니다.',
        'message': storage_message if config and enabled and not ready else None if config else
            'Earthdata 앱 등록 정보가 미설정이거나 로컬 세션의 허용 callback이 아닙니다. 공개 운영에는 공유 암호화 저장소가 필요합니다.'}))


def start():
    config = settings()
    if not config:
        return _no_store(JSONResponse(status_code=503, content={'error': {
            'code': 'EARTHDATA_NOT_CONFIGURED', 'message': 'Earthdata 앱 등록 정보가 필요합니다.'}}))
    store = _store(config)
    if _persistence_enabled() and (not store or not store.ready):
        return _no_store(JSONResponse(status_code=503, content={'error': {
            'code': 'EARTHDATA_STORAGE_UNAVAILABLE', 'message': earthdata_store.ISOLATION_MESSAGE
                if store and store.isolation_required else '암호화 세션 저장을 준비하지 못했습니다.'}}))
    state = secrets.token_urlsafe(32)
    with _lock:
        _prune(time.monotonic())
        if len(_pending) >= MAX_SESSIONS:
            return _no_store(JSONResponse(status_code=503, content={'error': {
                'code': 'EARTHDATA_BUSY', 'message': '로그인 요청이 많습니다. 잠시 후 다시 시도하세요.'}}))
        _pending[state] = time.monotonic() + FLOW_SECONDS
    url = EARTHDATA_ORIGIN + '/oauth/authorize?' + urlencode({
        'response_type': 'code', 'client_id': config.client_id,
        'redirect_uri': config.redirect_uri, 'state': state})
    response = RedirectResponse(url, status_code=302)
    response.set_cookie(STATE_COOKIE, state, max_age=FLOW_SECONDS, httponly=True,
                        secure=config.secure_cookie, samesite='lax', path=CALLBACK_PATH)
    return _no_store(response)


def parse_grant(data, previous_refresh=None):
    if not isinstance(data, dict):
        raise ValueError('Invalid Earthdata token response')
    token = data.get('access_token')
    token_type = data.get('token_type', 'Bearer')
    if not isinstance(token, str) or not token or len(token)>16384 or str(token_type).lower() != 'bearer':
        raise ValueError('Invalid Earthdata token response')
    # No guessed token lifetime, no implicit immortal refresh session.
    lifetime = data.get('expires_in')
    if isinstance(lifetime, bool) or not str(lifetime).isdigit() or not 0 < int(lifetime) <= 30*86400:
        raise ValueError('Invalid Earthdata token lifetime')
    refresh = data.get('refresh_token', previous_refresh)
    if refresh is not None and (not isinstance(refresh, str) or not refresh or len(refresh)>16384):
        raise ValueError('Invalid refresh response')
    return Grant(token, int(lifetime), refresh)


async def token_request(config, data):
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0),
                                 follow_redirects=False) as client:
        response = await client.post(EARTHDATA_ORIGIN + '/oauth/token',
            auth=(config.client_id, config.client_secret),
            data=data)
        response.raise_for_status()
        data = response.json()
    return data


async def exchange_code(config: Settings, code: str):
    return parse_grant(await token_request(config, {'grant_type':'authorization_code',
        'code':code, 'redirect_uri':config.redirect_uri}))


async def exchange_refresh(config: Settings, refresh: str):
    # Only an OAuth refresh_token actually issued in a token response is used here.
    # The EDL GUI User Token /api/users/renew_token API is deliberately not called.
    return parse_grant(await token_request(config, {'grant_type':'refresh_token',
        'refresh_token':refresh}), previous_refresh=refresh)


def _return_to_site(result: str):
    # Fixed result values only; never place provider errors, codes or tokens in the URL.
    return RedirectResponse('/?earthdata=' + result, status_code=303)


async def callback(request: Request, code: str | None = None,
                   state: str | None = None, error: str | None = None):
    config = settings()
    if not config:
        return _no_store(_return_to_site('unavailable'))
    cookie = request.cookies.get(STATE_COOKIE)
    valid = bool(state and cookie and len(state) <= 256 and hmac.compare_digest(state, cookie))
    with _lock:
        _prune(time.monotonic())
        valid = valid and state in _pending
        if valid:
            _pending.pop(state, None)
    if not valid:
        response = _return_to_site('invalid_state')
    elif error:
        response = _return_to_site('denied')
    elif not code or len(code) > 4096:
        response = _return_to_site('failed')
    else:
        try:
            grant = await exchange_code(config, code)
            sid = secrets.token_urlsafe(32)
            with _lock:
                _prune(time.monotonic())
                if len(_sessions) >= MAX_SESSIONS:
                    raise ValueError('Too many sessions')
                duration = PERSIST_SESSION_SECONDS if _persistence_enabled() else SESSION_SECONDS
                now, epoch = time.monotonic(), time.time()
                session = Session(grant, now+grant.lifetime, now+duration,
                    epoch_expires_at=epoch+grant.lifetime, epoch_deadline=epoch+duration,
                    fingerprint=_fingerprint(config))
                _save(sid, session, config)
                # A new login replaces this browser's previous grant, including on disk.
                previous_sid = request.cookies.get(SESSION_COOKIE)
                if previous_sid and len(previous_sid) <= 256:
                    _sessions.pop(previous_sid, None)
                    try:
                        _discard(previous_sid, config)
                    except earthdata_store.StorageError:
                        _discard(sid, config)
                        raise
                _sessions[sid] = session
            response = _return_to_site('connected')
            response.set_cookie(SESSION_COOKIE, sid, max_age=duration, httponly=True,
                                secure=config.secure_cookie, samesite='lax',
                                path='/api')
        except (httpx.HTTPError, ValueError, asyncio.TimeoutError, earthdata_store.StorageError):
            response = _return_to_site('failed')
    response.delete_cookie(STATE_COOKIE, path=CALLBACK_PATH)
    return _no_store(response)


def logout(request: Request):
    config = settings()
    if not config or request.headers.get('origin') != config.origin:
        return _no_store(JSONResponse(status_code=403, content={'error': {
            'code': 'INVALID_ORIGIN', 'message': '사이트에서 다시 시도하세요.'}}))
    sid = request.cookies.get(SESSION_COOKIE)
    if not sid or len(sid) > 256:
        return _no_store(JSONResponse(status_code=503, content={'connected': False,
            'storage_disposed': False, 'revocation_recorded': False, 'session_missing': True,
            'message': '원래 연결 식별 쿠키가 없어 이전 grant 폐기를 확인할 수 없습니다. 저장소 격리와 NASA 측 철회를 별도로 확인하세요.'}))
    disposed, recorded, isolation_required = True, False, False
    with _lock:
        _block_session(sid)
        session = _sessions.pop(sid, None)
        if session:
            session.state = 'reconnection_required'
            session.grant = Grant('', 0)
        try:
            recorded = _discard(sid, config)
        except earthdata_store.StorageError as error:
            disposed = False
            recorded = error.revocation_recorded
            isolation_required = error.isolation_required
    response = JSONResponse({'connected': False, 'storage_disposed': disposed,
        'revocation_recorded': recorded, 'cleanup_required': not disposed,
        'storage_isolation_required': isolation_required,
        'message': None if disposed else
            earthdata_store.ISOLATION_MESSAGE + ' 폐기를 확인하지 못했으며 재시도용 쿠키를 유지했습니다.' if isolation_required else
            '폐기 기록은 저장했지만 DB 삭제에 실패했습니다. 현재 연결 사용과 재시작 후 해당 SID 복원은 차단합니다. 쿠키를 유지했으므로 권한 복구 후 연결 해제를 다시 시도하세요.' if recorded else
            '현재 프로세스의 연결 사용만 차단했습니다. 모든 지속 쓰기 실패 시 재시작 후 영구 폐기는 보장할 수 없습니다. 쿠키를 유지했으므로 권한 복구 후 다시 시도하고, 필요하면 서버 종료 후 저장소 전체 격리 및 NASA 측 철회를 확인하세요.'},
        status_code=200 if disposed else 503)
    if disposed:
        response.delete_cookie(SESSION_COOKIE, path='/api/auth/earthdata')
        response.delete_cookie(SESSION_COOKIE, path='/api')
    return _no_store(response)


def providers_status(request: Request):
    from . import operator_access as operator
    nasa = json.loads(status(request).body)
    rows=[
        {'provider_id': 'earth-search', 'configured': False, 'connected': False,
         'integration': 'public_catalog_and_selected_public_assets', 'storage': 'none',
         'message': 'Earth Search 공개 검색은 연결되어 있습니다. USGS 로그인·AWS requester-pays 인증은 미연결입니다. '
                    'USGS 공식 ERS/M2M 앱 등록·이용 권한과 제품별 다운로드 경로를 별도로 준비·검증해야 합니다. '
                    'https://www.usgs.gov/media/files/m2m-application-token-documentation'},
        {'provider_id': 'copernicus', 'configured': False, 'connected': False,
         'integration': 'public_catalog_only', 'storage': 'none',
         'message': 'Copernicus 공개 검색만 연결되어 있으며 CDSE 원본 인증은 미연결입니다. '
                    'CDSE 공식 계정·승인 흐름과 대상 Asset 호환성을 별도로 준비·검증해야 합니다. '
                    'https://documentation.dataspace.copernicus.eu/APIs/Token.html'},
        {'provider_id': 'nasa-cmr', 'configured': nasa['configured'], 'connected': nasa['connected'],
         'integration': 'earthdata_local_oauth', 'storage': nasa['storage'],
         'message': nasa['message'] or ('Earthdata 계정 연결이며 대상 파일 접근·권한은 별도 확인해야 합니다. '
                    '로그아웃은 이 사이트의 저장 grant 폐기이며 NASA 전체 계정 토큰 폐기는 아닙니다. '
                    'https://urs.earthdata.nasa.gov/documentation/for_users/sso_process_overview')},
    ]
    for row,provider in zip(rows,('usgs','cdse','nasa')):
        if operator.enabled(provider):row.update(operator.public_status(provider))
    return _no_store(JSONResponse({'providers':rows}))
