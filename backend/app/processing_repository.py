"""Local single-server journal. Signed metadata, private files, no provider grants.

Only terminal public records and non-secret input are persisted. Running jobs
are never replayed after restart. SQLite transactions prevent partial records.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from contextlib import contextmanager
from .pixel_policy import QualityError

PRIVATE = Path(__file__).resolve().parent.parent / '.private'
_lease=None
_lease_path=None


def claim_worker():
    """Fail closed if a second process tries to execute on the same store."""
    global _lease,_lease_path
    from .artifact_store import ROOT
    path=ROOT/'worker.lock'
    if _lease is not None and _lease_path==path:return
    if _lease is not None:_lease.close();_lease=None
    ROOT.mkdir(parents=True,exist_ok=True)
    f=path.open('a+b')
    if not path.stat().st_size:f.write(b'0');f.flush()
    f.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        f.close();raise QualityError('다른 처리 worker가 이 보관소를 사용 중입니다. 로컬 단일 worker만 지원합니다.') from None
    _lease=f;_lease_path=path


def session_key():
    PRIVATE.mkdir(parents=True, exist_ok=True)
    path = PRIVATE / 'work-session.key'
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, 'wb') as f:
            f.write(secrets.token_bytes(32)); f.flush(); os.fsync(f.fileno())
    key = path.read_bytes()
    if len(key) != 32: raise RuntimeError('로컬 작업 소유권 키 손상. 자동 교체하지 않습니다.')
    return key


@contextmanager
def connection():
    # ROOT is deliberately the same overridable private root as the artifacts.
    from .artifact_store import ROOT
    ROOT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(ROOT / 'jobs.sqlite3', timeout=5)
    try:
        db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, owner TEXT NOT NULL, body TEXT NOT NULL, signature TEXT NOT NULL, expires REAL NOT NULL)')
        with db:yield db
    finally:db.close()


def signature(body):
    from .work_sessions import KEY
    return hmac.new(KEY, body.encode(), hashlib.sha256).hexdigest()


def save(job):
    from .artifact_store import safe_value
    # No asyncio Task, canonical URL payload, confirmation digest or cookie.
    value = {k: job.get(k) for k in ('job_id','owner','plan_id','idempotency_key','status','stage','created_at','updated_at','error','failure','result','artifact','input','events','expires_at')}
    if not value['job_id']: return
    value = safe_value(value, include_maps=True)
    body = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    if len(body.encode()) > 2_000_000: raise QualityError('작업 메타데이터 보관 상한 초과')
    with connection() as db:
        exists=db.execute('SELECT 1 FROM jobs WHERE id=?',(value['job_id'],)).fetchone()
        if not exists and db.execute('SELECT count(*) FROM jobs').fetchone()[0]>=100:
            raise QualityError('로컬 보관 작업 100개 상한입니다. 보관 만료 후 다시 실행하세요.')
        db.execute('INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?)', (value['job_id'], value['owner'], body, signature(body), time.time()))


def load(identifier, owner):
    if not owner: return None
    with connection() as db:
        row = db.execute('SELECT body,signature FROM jobs WHERE id=? AND owner=?', (identifier, owner)).fetchone()
    if not row: return None
    if not hmac.compare_digest(signature(row[0]), row[1]): raise QualityError('저장된 작업 메타데이터가 변경됐습니다. 재실행하지 않습니다.')
    value = json.loads(row[0])
    if value['status'] in ('queued','running'):
        value.update(status='failed',stage='서버 재시작으로 중단',error='서버 재시작 전 실행 중이던 작업입니다. 자동 재실행하지 않습니다.',artifact=None,result=None)
        save(value)
    return value


def owned_ids(owner):
    if not owner: return []
    with connection() as db:
        # Retain small tombstones for expired work, bounded by time and count.
        from .artifact_store import TTL
        db.execute('DELETE FROM jobs WHERE expires < ?', (time.time()-TTL-86400,))
        return [r[0] for r in db.execute('SELECT id FROM jobs WHERE owner=? ORDER BY expires DESC LIMIT 20', (owner,))]


def duplicate(owner, key):
    for identifier in owned_ids(owner):
        job = load(identifier, owner)
        if job and job['idempotency_key'] == key: return job
    return None
