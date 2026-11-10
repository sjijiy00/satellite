"""TEST ONLY public-origin checks, without credentials or external calls."""
import pytest
from fastapi import Request, HTTPException
from app import media_access, work_sessions, public_site


def request(origin):
    return Request({'type':'http','scheme':'https','server':('backend.example',443),
                    'path':'/media/inspect','headers':[(b'origin',origin.encode())]})


@pytest.fixture(autouse=True)
def anonymous(monkeypatch):
    monkeypatch.setattr(media_access.operator, 'enabled', lambda _: False)
    monkeypatch.setattr(media_access.auth, 'settings', lambda: None)
    monkeypatch.delenv('PUBLIC_APP_ORIGIN', raising=False)


def test_explicit_public_origin_allows_media_and_jobs(monkeypatch):
    monkeypatch.setenv('PUBLIC_APP_ORIGIN','https://test-only.pages.dev')
    for check in (media_access.same_origin, work_sessions.protect):
        check(request('https://test-only.pages.dev'))
        with pytest.raises(HTTPException) as error:
            check(request('https://other.pages.dev'))
        assert error.value.status_code == 403


@pytest.mark.parametrize('origin',['','*','http://test-only.pages.dev','https://test-only.pages.dev/',
    'https://user:password@test-only.pages.dev','https://test-only.pages.dev?query=1'])
def test_invalid_configuration_does_not_allow_public_site(monkeypatch,origin):
    monkeypatch.setenv('PUBLIC_APP_ORIGIN',origin)
    assert public_site.public_origin() is None
    with pytest.raises(HTTPException):media_access.same_origin(request('https://test-only.pages.dev'))


def test_local_development_still_allowed():
    media_access.same_origin(request('http://127.0.0.1:3000'))
    work_sessions.protect(request('http://127.0.0.1:3000'))


def test_operator_origin_policy_is_not_overridden(monkeypatch):
    monkeypatch.setenv('PUBLIC_APP_ORIGIN','https://test-only.pages.dev')
    monkeypatch.setenv('OPERATOR_PUBLIC_ORIGIN','https://operator.example')
    monkeypatch.setattr(media_access.operator,'enabled',lambda _:True)
    with pytest.raises(HTTPException):media_access.same_origin(request('https://test-only.pages.dev'))
