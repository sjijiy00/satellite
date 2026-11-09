"""Never expose signed URLs or URL credentials from upstream catalogues."""
from urllib.parse import urlsplit, parse_qsl


def safe_url(value, schemes=('https', 'http')):
    if not isinstance(value, str):
        return None
    try:
        u = urlsplit(value)
        if u.scheme not in schemes or not u.netloc or u.username or u.password or u.fragment:
            return None
        for key, _ in parse_qsl(u.query, keep_blank_values=True):
            key = key.lower().replace('-', '_')
            if key == 'sort_key':  # CMR's documented public sort parameter, not a credential.
                continue
            if any(part in key for part in ('token', 'key', 'sign', 'credential', 'auth', 'secret', 'password')) or key in ('sig', 'se', 'sp', 'sv', 'expires', 'policy'):
                return None
        return value
    except ValueError:
        return None
