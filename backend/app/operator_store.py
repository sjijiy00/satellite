"""Operator grants only: user-scope DPAPI + transactional, shared SQLite state.

An ambiguous renewal is durably blocked BEFORE contacting the issuer. A crash
cannot silently fall back to the seed that renewal may already have invalidated.
Not a portable/public deployment secret store; no visitor sessions live here.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from . import earthdata_store as crypto
from .provider_transfer import TransferError

DEFAULT_PATH=Path(__file__).resolve().parents[1]/'.private/operator/access.sqlite3'
LIMIT_BYTES=1024**3
CDSE_LIMIT_BYTES=3*1024**3
LIMIT_REQUESTS=120


class Store:
    def __init__(self,path=None):
        self.path=Path(path or os.getenv('OPERATOR_STORE_PATH') or DEFAULT_PATH)

    @contextmanager
    def db(self):
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            if self.path.is_symlink() or self.path.parent.is_symlink():raise ValueError()
            crypto._restrict_directory(self.path.parent)
            con=sqlite3.connect(self.path,timeout=1,isolation_level=None)
            try:
                con.execute('PRAGMA synchronous=FULL')
                con.execute('CREATE TABLE IF NOT EXISTS grants(provider TEXT PRIMARY KEY, revision INTEGER, fingerprint TEXT, state TEXT, generation INTEGER, payload BLOB)')
                con.execute('CREATE TABLE IF NOT EXISTS usage(provider TEXT, hour INTEGER, requests INTEGER, bytes INTEGER, PRIMARY KEY(provider,hour))')
                con.execute('CREATE TABLE IF NOT EXISTS active(id TEXT PRIMARY KEY, provider TEXT, deadline REAL)')
                con.execute('CREATE TABLE IF NOT EXISTS seeds(provider TEXT, fingerprint TEXT, PRIMARY KEY(provider,fingerprint))')
                con.execute('BEGIN IMMEDIATE')
                yield con
                con.commit()
            except BaseException:
                con.rollback();raise
            finally:con.close()
        except (OSError,sqlite3.Error,crypto.StorageError,ValueError):
            raise TransferError('operator_storage_unavailable') from None

    def encode(self,provider,value):
        raw=json.dumps(value,separators=(',',':')).encode()
        if len(raw)>32768:raise TransferError('operator_invalid_response')
        return crypto.protect(raw,('operator-v1:'+provider).encode())

    def decode(self,provider,blob):
        return json.loads(crypto.unprotect(blob,('operator-v1:'+provider).encode()))

    def load(self,provider,revision,fingerprint,seed):
        with self.db() as con:
            row=con.execute('SELECT revision,fingerprint,state,generation,payload FROM grants WHERE provider=?',(provider,)).fetchone()
            if row and (revision<row[0] or revision==row[0] and fingerprint!=row[1]):raise TransferError('operator_configuration_changed')
            if not row or revision>row[0]:
                # A stored-only restart may use an existing encrypted grant, never
                # create a new generation without an independently supplied seed.
                if seed is None:raise TransferError('operator_not_ready')
                known=con.execute('SELECT 1 FROM seeds WHERE provider=? AND fingerprint=?',(provider,fingerprint)).fetchone()
                # Static credentials are not invalidated by session renewal. An
                # administrator may explicitly retry them with a higher revision,
                # except after local revocation. Rotating token seeds never re-enter.
                retry_static=row and row[2]!='revoked' and row[1]==fingerprint and (provider=='usgs' or provider=='cdse' and not seed.get('refresh'))
                if known and not retry_static:raise TransferError('operator_reused_seed')
                if con.execute('SELECT COUNT(*) FROM seeds').fetchone()[0]>=1000:raise TransferError('operator_storage_unavailable')
                generation=(row[3]+1) if row else 1
                blob=self.encode(provider,seed)
                con.execute('INSERT OR IGNORE INTO seeds VALUES(?,?)',(provider,fingerprint))
                con.execute('INSERT OR REPLACE INTO grants VALUES(?,?,?,?,?,?)',(provider,revision,fingerprint,'active',generation,blob))
                return {'state':'active','generation':generation,**seed}
            return {'state':row[2],'generation':row[3],**self.decode(provider,row[4])}

    def existing_fingerprint(self,provider,revision):
        """Bind an explicit stored-grant restart to the exact existing generation."""
        if not self.path.exists():raise TransferError('operator_not_ready')
        with self.db() as con:
            row=con.execute('SELECT revision,fingerprint FROM grants WHERE provider=?',(provider,)).fetchone()
            if not row:raise TransferError('operator_not_ready')
            if row[0]!=revision:raise TransferError('operator_configuration_changed')
            return row[1]

    def change(self,provider,generation,state,value=None):
        with self.db() as con:
            row=con.execute('SELECT generation FROM grants WHERE provider=?',(provider,)).fetchone()
            if not row or row[0]!=generation:raise TransferError('operator_changed')
            if value is None:con.execute('UPDATE grants SET state=?,generation=generation+1 WHERE provider=?',(state,provider))
            else:con.execute('UPDATE grants SET state=?,generation=generation+1,payload=? WHERE provider=?',(state,self.encode(provider,value),provider))
            return generation+1

    def inspect(self,provider):
        with self.db() as con:
            row=con.execute('SELECT revision,state,generation FROM grants WHERE provider=?',(provider,)).fetchone()
            return {'revision':row[0],'state':row[1],'generation':row[2]} if row else {'state':'not_initialized'}

    def revoke(self,provider):
        with self.db() as con:
            if not con.execute('SELECT 1 FROM grants WHERE provider=?',(provider,)).fetchone():raise TransferError('operator_not_initialized')
            # Keep the revision/fingerprint tombstone. Never delete the seed record.
            con.execute("UPDATE grants SET state='revoked',generation=generation+1,payload=? WHERE provider=?",(self.encode(provider,{}),provider))

    def enter(self,provider,identifier,deadline_seconds=125):
        now=time.time();hour=int(now//3600)
        with self.db() as con:
            con.execute('DELETE FROM active WHERE deadline<?',(now,))
            con.execute('DELETE FROM usage WHERE hour<?',(hour-1,))
            if con.execute('SELECT 1 FROM active WHERE id=?',(identifier,)).fetchone():raise TransferError('operator_busy')
            if con.execute('SELECT COUNT(*) FROM active WHERE provider=?',(provider,)).fetchone()[0]>=2:raise TransferError('operator_busy')
            con.execute('INSERT OR IGNORE INTO usage VALUES(?,?,0,0)',(provider,hour))
            used=con.execute('SELECT requests FROM usage WHERE provider=? AND hour=?',(provider,hour)).fetchone()[0]
            if used>=LIMIT_REQUESTS:raise TransferError('operator_quota')
            con.execute('UPDATE usage SET requests=requests+1 WHERE provider=? AND hour=?',(provider,hour))
            con.execute('INSERT INTO active VALUES(?,?,?)',(identifier,provider,now+deadline_seconds))

    def leave(self,identifier):
        with self.db() as con:con.execute('DELETE FROM active WHERE id=?',(identifier,))

    def charge(self,provider,amount):
        hour=int(time.time()//3600)
        with self.db() as con:
            con.execute('INSERT OR IGNORE INTO usage VALUES(?,?,0,0)',(provider,hour))
            used=con.execute('SELECT bytes FROM usage WHERE provider=? AND hour=?',(provider,hour)).fetchone()[0]
            if used+amount>(CDSE_LIMIT_BYTES if provider=='cdse' else LIMIT_BYTES):raise TransferError('operator_quota')
            con.execute('UPDATE usage SET bytes=bytes+? WHERE provider=? AND hour=?',(amount,provider,hour))

    def count_request(self,provider):
        hour=int(time.time()//3600)
        with self.db() as con:
            con.execute('INSERT OR IGNORE INTO usage VALUES(?,?,0,0)',(provider,hour))
            used=con.execute('SELECT requests FROM usage WHERE provider=? AND hour=?',(provider,hour)).fetchone()[0]
            if used>=LIMIT_REQUESTS:raise TransferError('operator_quota')
            con.execute('UPDATE usage SET requests=requests+1 WHERE provider=? AND hour=?',(provider,hour))


def fingerprint(values):
    return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()
