"""Explicit public browser origin; does not enable CORS or provider credentials."""
import os
from urllib.parse import urlsplit


def public_origin():
    value = os.getenv('PUBLIC_APP_ORIGIN', '').strip()
    try:
        parsed = urlsplit(value)
        if (parsed.scheme == 'https' and parsed.hostname and not parsed.username
                and not parsed.password and not parsed.path and not parsed.query and not parsed.fragment):
            return value
    except ValueError:
        pass
    return None
