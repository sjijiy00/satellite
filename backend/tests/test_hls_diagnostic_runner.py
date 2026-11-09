"""TEST ONLY: real-auth diagnostic is fail-closed and never rotates a token."""
import asyncio
import importlib.util
from pathlib import Path
import pytest
import httpx
from app import provider_transfer as transfer

spec=importlib.util.spec_from_file_location('hls_diagnostic_runner',Path(__file__).resolve().parents[2]/'scripts/diagnose-hls-local.py')
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_forced_renewal_is_rejected_before_config_or_store(monkeypatch):
    def forbidden(*args):raise AssertionError('Credential config/store must not be called')
    monkeypatch.setattr(runner.operator,'config',forbidden)
    monkeypatch.setattr(runner.operator,'store',forbidden)
    with pytest.raises(transfer.TransferError,match='operator_reconnection_required'):
        asyncio.run(runner.existing_token_only('nasa',force=True))


def test_uninitialized_store_is_not_seeded(monkeypatch):
    monkeypatch.setattr(runner.operator,'enabled',lambda *_:True)
    monkeypatch.setattr(runner.operator,'config',lambda *_:({},1,'TEST_ONLY_FINGERPRINT'))
    class Store:
        def inspect(self,*args):return {'state':'not_initialized'}
        def load(self,*args):raise AssertionError('No seed adoption')
    monkeypatch.setattr(runner.operator,'store',Store)
    with pytest.raises(transfer.TransferError,match='operator_not_initialized'):
        asyncio.run(runner.existing_token_only('nasa'))


def test_new_environment_revision_cannot_adopt_a_new_grant(monkeypatch):
    monkeypatch.setattr(runner.operator,'enabled',lambda *_:True)
    monkeypatch.setattr(runner.operator,'config',lambda *_:({},2,'TEST_ONLY_FINGERPRINT'))
    class Store:
        def inspect(self,*args):return {'state':'active','revision':1}
        def load(self,*args):raise AssertionError('No new revision adoption')
    monkeypatch.setattr(runner.operator,'store',Store)
    with pytest.raises(transfer.TransferError,match='operator_configuration_changed'):
        asyncio.run(runner.existing_token_only('nasa'))


@pytest.mark.parametrize('status,media,expected',[(429,'application/json','provider_busy'),(200,'text/html','login_page')])
def test_minimum_request_stops_rate_limit_and_login(monkeypatch,status,media,expected):
    original=httpx.AsyncClient;calls=[]
    def handle(request):calls.append(request);return httpx.Response(status,content=b'TEST ONLY',headers={'content-type':media})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    async def validate(*args):pass
    monkeypatch.setattr(transfer,'validate_destination',validate)
    with pytest.raises(transfer.TransferError,match=expected):
        asyncio.run(runner.minimum_browse('https://example.test/TEST_ONLY'))
    assert len(calls)==1 and 'authorization' not in calls[0].headers
