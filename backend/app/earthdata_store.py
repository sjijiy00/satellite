"""Bounded, user-scope DPAPI grant storage for the local single-process launcher.

Only ciphertext, a hashed browser-session ID, configuration fingerprint and expiry
are stored. No portable key file, machine-scope DPAPI or third-party dependency.
Concurrent server processes are deliberately unsupported.
"""
import ctypes
from contextlib import contextmanager
from ctypes import wintypes
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import sqlite3
import time

STORE_PATH = Path(__file__).resolve().parents[1] / '.private' / 'earthdata' / 'sessions.sqlite3'
MAX_SESSIONS = 1000
MAX_BLOB_BYTES = 65536
MAX_DATABASE_BYTES = 80 * 1024 * 1024
MAX_SESSION_SECONDS = 30 * 86400
STORE_VERSION = 2
MAX_REVOCATIONS = 1000
MAX_JOURNAL_BYTES = 256 * 1024
MAX_STORE_FILES = 16
ISOLATION_MESSAGE = ('이전 포맷 또는 다른 앱 설정의 저장소는 자동 복원·초기화하지 않습니다. '
    '서버를 종료하고 backend/.private/earthdata 폴더 전체를 별도의 보호된 위치에 격리한 뒤 '
    '새 빈 저장소로 시작하세요. 기존 연결의 제공처 측 철회는 NASA에서 별도로 확인해야 합니다.')


class StorageError(Exception):
    """Public callers must use a fixed error, never an underlying OS exception."""
    def __init__(self, message='Earthdata storage unavailable', *, revocation_recorded=False,
                 isolation_required=False):
        super().__init__(message)
        self.revocation_recorded = revocation_recorded
        self.isolation_required = isolation_required


class FormatError(StorageError):
    pass


class _Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi(data: bytes, entropy: bytes, *, decrypt=False):
    if os.name != 'nt':
        raise StorageError('DPAPI unavailable')
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    data_buffer = ctypes.create_string_buffer(data)
    entropy_buffer = ctypes.create_string_buffer(entropy)
    source = _Blob(len(data), ctypes.cast(data_buffer, ctypes.POINTER(ctypes.c_ubyte)))
    extra = _Blob(len(entropy), ctypes.cast(entropy_buffer, ctypes.POINTER(ctypes.c_ubyte)))
    result = _Blob()
    operation = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    operation.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.POINTER(_Blob),
                          ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
    operation.restype = wintypes.BOOL
    # UI_FORBIDDEN only: deliberately never CRYPTPROTECT_LOCAL_MACHINE.
    if not operation(ctypes.byref(source), None, ctypes.byref(extra), None, None, 1,
                     ctypes.byref(result)):
        raise StorageError('DPAPI operation failed') from None
    try:
        if result.size > MAX_JOURNAL_BYTES:
            raise StorageError('Encrypted grant too large')
        return ctypes.string_at(result.data, result.size)
    finally:
        kernel.LocalFree(ctypes.cast(result.data, ctypes.c_void_p))


def protect(data, entropy):
    return _dpapi(data, entropy)


def unprotect(data, entropy):
    return _dpapi(data, entropy, decrypt=True)


def _restrict_directory(directory):
    """Protect inheritance: only this Windows user and SYSTEM get access."""
    if os.name != 'nt':
        raise StorageError('DPAPI unavailable')
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                          wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
    advapi.SetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
    token, sid_text, descriptor = wintypes.HANDLE(), wintypes.LPWSTR(), ctypes.c_void_p()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise StorageError('Storage permissions unavailable')
    try:
        size = wintypes.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
            raise StorageError('Storage permissions unavailable')
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        if not advapi.ConvertSidToStringSidW(sid, ctypes.byref(sid_text)):
            raise StorageError('Storage permissions unavailable')
        sddl = f'D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;{sid_text.value})'
        if not advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1,
                ctypes.byref(descriptor), None):
            raise StorageError('Storage permissions unavailable')
        # DACL_SECURITY_INFORMATION | PROTECTED_DACL_SECURITY_INFORMATION.
        if not advapi.SetFileSecurityW(str(directory), 0x80000004, descriptor):
            raise StorageError('Storage permissions unavailable')
    finally:
        if descriptor:
            kernel.LocalFree(descriptor)
        if sid_text:
            kernel.LocalFree(ctypes.cast(sid_text, ctypes.c_void_p))
        kernel.CloseHandle(token)


def session_key(sid):
    if not isinstance(sid, str) or not 1 <= len(sid) <= 256:
        raise StorageError('Invalid session ID')
    return hashlib.sha256(sid.encode()).hexdigest()


def _atomic_write(path, content):
    """Flush a sibling file, replace atomically, then verify the durable bytes."""
    temporary = path.with_name(path.name + '.' + secrets.token_hex(8) + '.tmp')
    try:
        with temporary.open('xb') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        if os.name == 'nt':
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.MoveFileExW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
            kernel.MoveFileExW.restype = wintypes.BOOL
            # REPLACE_EXISTING | WRITE_THROUGH, same directory/volume.
            if not kernel.MoveFileExW(str(temporary), str(path), 0x1 | 0x8):
                raise StorageError('Revocation journal replacement failed')
        else:
            os.replace(temporary, path)
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        with path.open('rb') as stored:
            if stored.read(MAX_JOURNAL_BYTES + 1) != content:
                raise StorageError('Revocation journal verification failed')
    finally:
        temporary.unlink(missing_ok=True)


class GrantStore:
    def __init__(self, path, fingerprint):
        self.path = Path(path)
        self.journal_path = self.path.with_name(self.path.name + '.revocations')
        self.fingerprint = fingerprint
        self.entropy = ('satellite-earthdata-v2:' + fingerprint).encode()
        self.ready = False
        self.format_valid = False
        self.protection_ready = False
        self.isolation_required = False
        self.error_code = 'storage_unavailable'
        self.store_id = None
        try:
            exists = self.path.exists()
            # Existing files are inspected read-only BEFORE any migration, ACL or pruning.
            if exists:
                self._existing_format()
            elif self.journal_path.exists():
                raise FormatError('incomplete_store')
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.parent.is_symlink() or self.path.is_symlink() or self.journal_path.is_symlink():
                raise StorageError('Unsafe storage path')
            _restrict_directory(self.path.parent)
            for file in (self.path, self.journal_path):
                if file.exists():
                    _restrict_directory(file)
            probe = secrets.token_bytes(32)
            if unprotect(protect(probe, self.entropy), self.entropy) != probe:
                raise StorageError('DPAPI readiness failed')
            self.protection_ready = True
            if exists:
                self._read_journal()
            else:
                self.store_id = secrets.token_hex(32)
                with self._connect() as database:
                    database.execute('CREATE TABLE metadata (version INTEGER, fingerprint TEXT, store_id TEXT)')
                    database.execute('INSERT INTO metadata VALUES (?, ?, ?)',
                                     (STORE_VERSION, self.fingerprint, self.store_id))
                    database.execute('CREATE TABLE grants '
                        '(sid_hash TEXT PRIMARY KEY, payload BLOB NOT NULL, deadline REAL NOT NULL, '
                        'fingerprint TEXT NOT NULL)')
                    database.execute(f'PRAGMA user_version = {STORE_VERSION}')
                    self._write_journal({})
                self.format_valid = True
            with self._connect() as database:
                if database.execute('SELECT count(*) FROM grants').fetchone()[0] > MAX_SESSIONS:
                    raise StorageError('Session limit exceeded')
                # Different fingerprints are not silently removed from an existing store.
                if database.execute('SELECT 1 FROM grants WHERE fingerprint != ? LIMIT 1',
                                    (self.fingerprint,)).fetchone():
                    raise FormatError('configuration_mismatch')
                self._prune(database)
            self.ready = True
            self.error_code = None
        except FormatError as error:
            self.isolation_required = True
            self.error_code = str(error)  # Fixed internal enum, never provider/OS data.
        except (OSError, sqlite3.Error, StorageError, ValueError, TypeError):
            self.ready = False

    def _existing_format(self):
        if self.path.stat().st_size > MAX_DATABASE_BYTES:
            raise StorageError('Storage size limit exceeded')
        database = sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True, timeout=1)
        try:
            version = database.execute('PRAGMA user_version').fetchone()[0]
            if version != STORE_VERSION:
                raise FormatError('legacy_or_unknown_format')
            try:
                rows = database.execute('SELECT version, fingerprint, store_id FROM metadata LIMIT 2').fetchall()
            except sqlite3.Error:
                raise FormatError('invalid_format') from None
            if (len(rows) != 1 or rows[0][0] != STORE_VERSION
                    or not isinstance(rows[0][2], str) or len(rows[0][2]) != 64):
                raise FormatError('invalid_format')
            if rows[0][1] != self.fingerprint:
                raise FormatError('configuration_mismatch')
            self.store_id = rows[0][2]
            self.format_valid = True
        finally:
            database.close()

    @contextmanager
    def _connect(self):
        if self.path.exists() and self.path.stat().st_size > MAX_DATABASE_BYTES:
            raise StorageError('Storage size limit exceeded')
        database = sqlite3.connect(self.path, timeout=1)
        try:
            page_size = database.execute('PRAGMA page_size').fetchone()[0]
            database.execute(f'PRAGMA max_page_count = {MAX_DATABASE_BYTES // page_size}')
            database.execute('PRAGMA journal_size_limit = 0')
            database.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_BLOB_BYTES + 4096)
            with database:
                yield database
        finally:
            database.close()

    def _journal_entropy(self):
        return self.entropy + b':revocations:' + self.store_id.encode()

    def _read_journal(self):
        self._check_file_count()
        if self.journal_path.is_symlink():
            raise StorageError('Unsafe revocation journal')
        with self.journal_path.open('rb') as source:
            encrypted = source.read(MAX_JOURNAL_BYTES + 1)
        if not encrypted or len(encrypted) > MAX_JOURNAL_BYTES:
            raise StorageError('Revocation journal size limit')
        data = json.loads(unprotect(encrypted, self._journal_entropy()))
        if (not isinstance(data, dict) or data.get('version') != STORE_VERSION
                or data.get('fingerprint') != self.fingerprint or data.get('store_id') != self.store_id
                or not isinstance(data.get('revoked'), dict) or len(data['revoked']) > MAX_REVOCATIONS):
            raise StorageError('Invalid revocation journal')
        now = time.time()
        for key, deadline in data['revoked'].items():
            if (not isinstance(key, str) or len(key) != 64 or any(c not in '0123456789abcdef' for c in key)
                    or isinstance(deadline, bool) or not isinstance(deadline, (int, float))
                    or not math.isfinite(deadline) or deadline > now + MAX_SESSION_SECONDS):
                raise StorageError('Invalid revocation record')
        return data['revoked']

    def _write_journal(self, revoked):
        self._check_file_count()
        payload = json.dumps({'version': STORE_VERSION, 'store_id': self.store_id,
            'fingerprint': self.fingerprint, 'revoked': revoked}, separators=(',', ':'), allow_nan=False).encode()
        if len(revoked) > MAX_REVOCATIONS or len(payload) > MAX_JOURNAL_BYTES - 4096:
            raise StorageError('Revocation journal limit')
        encrypted = protect(payload, self._journal_entropy())
        _atomic_write(self.journal_path, encrypted)
        if self._read_journal() != revoked:
            raise StorageError('Revocation journal verification failed')

    def _check_file_count(self):
        # Bound abandoned atomic-write temporary files too; never silently remove user files.
        with os.scandir(self.path.parent) as entries:
            for index, _ in enumerate(entries, 1):
                if index > MAX_STORE_FILES:
                    raise StorageError('Storage file count limit')

    def _prune(self, database):
        database.execute('DELETE FROM grants WHERE deadline <= ?', (time.time(),))

    def _fail(self, *, revocation_recorded=False):
        self.ready = False
        self.error_code = 'storage_unavailable'
        raise StorageError(revocation_recorded=revocation_recorded,
                           isolation_required=self.isolation_required) from None

    def is_revoked(self, sid):
        try:
            return self._read_journal().get(session_key(sid), 0) > time.time()
        except (OSError, StorageError, ValueError, TypeError):
            self._fail()

    def save(self, sid, payload):
        if not self.ready:
            self._fail()
        try:
            if self.is_revoked(sid):
                raise StorageError('Session revoked')
            now = time.time()
            if not now < payload['deadline'] <= now + MAX_SESSION_SECONDS:
                raise StorageError('Invalid session deadline')
            payload = payload | {'sid_hash': session_key(sid)}
            encoded = json.dumps(payload, separators=(',', ':'), allow_nan=False).encode()
            if len(encoded) > MAX_BLOB_BYTES - 4096:
                raise StorageError('Grant too large')
            ciphertext = protect(encoded, self.entropy)
            if len(ciphertext) > MAX_BLOB_BYTES:
                raise StorageError('Grant too large')
            with self._connect() as database:
                self._prune(database)
                key = session_key(sid)
                exists = database.execute('SELECT 1 FROM grants WHERE sid_hash = ?', (key,)).fetchone()
                if not exists and database.execute('SELECT count(*) FROM grants').fetchone()[0] >= MAX_SESSIONS:
                    raise StorageError('Session limit exceeded')
                database.execute('INSERT OR REPLACE INTO grants VALUES (?, ?, ?, ?)',
                    (key, ciphertext, payload['deadline'], self.fingerprint))
        except (OSError, sqlite3.Error, StorageError, ValueError, KeyError, TypeError):
            self._fail()

    def load(self, sid):
        if not self.ready:
            self._fail()
        try:
            if self.is_revoked(sid):
                return None
            with self._connect() as database:
                row = database.execute('SELECT payload, deadline, fingerprint FROM grants WHERE sid_hash = ?',
                                       (session_key(sid),)).fetchone()
            if not row:
                return None
            now = time.time()
            if (row[2] != self.fingerprint or not now < row[1] <= now + MAX_SESSION_SECONDS
                    or len(row[0]) > MAX_BLOB_BYTES):
                self.delete(sid)
                return None
            try:
                payload = json.loads(unprotect(row[0], self.entropy))
                deadline, expiry = payload['deadline'], payload['expires_at']
                if (not isinstance(deadline, (int, float)) or isinstance(deadline, bool)
                        or not isinstance(expiry, (int, float)) or isinstance(expiry, bool)
                        or not math.isfinite(expiry) or deadline != row[1]
                        or payload.get('sid_hash') != session_key(sid)
                        or expiry > now + MAX_SESSION_SECONDS
                        or not now < deadline <= now + MAX_SESSION_SECONDS):
                    raise ValueError('Invalid grant')
                return payload
            except (StorageError, ValueError, KeyError, TypeError):
                self.delete(sid)
                return None
        except (OSError, sqlite3.Error, StorageError, ValueError, TypeError):
            self._fail()

    def _delete_grant(self, key):
        with self._connect() as database:
            database.execute('DELETE FROM grants WHERE sid_hash = ?', (key,))
        with self._connect() as database:
            if database.execute('SELECT 1 FROM grants WHERE sid_hash = ?', (key,)).fetchone():
                raise StorageError('Grant deletion not verified')

    def delete(self, sid):
        recorded = False
        try:
            if not self.format_valid or not self.protection_ready:
                raise StorageError('Store isolation required')
            key, now = session_key(sid), time.time()
            # Never replace an unreadable journal with an empty one: that loses revocations.
            revoked = {key: deadline for key, deadline in self._read_journal().items() if deadline > now}
            revoked[key] = now + MAX_SESSION_SECONDS
            self._write_journal(revoked)
            recorded = True
            self._delete_grant(key)
            self.ready = True
            self.error_code = None
        except (OSError, sqlite3.Error, StorageError, ValueError, TypeError):
            self._fail(revocation_recorded=recorded)
