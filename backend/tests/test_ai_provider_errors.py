"""TEST ONLY bounded provider-error transport; no real API calls."""
import asyncio,json
import httpx
import pytest
from app import ai_interpretation as ai
from app.ai_interpretation import _send as transport_send

@pytest.mark.parametrize('code',sorted(ai.QUOTA_CODES))
def test_billing_codes_are_actionable_without_exposing_provider_message(monkeypatch,code):
    monkeypatch.setenv('AI_NL_ENABLED','1');monkeypatch.setenv('AI_NL_PROVIDER','openai');monkeypatch.setenv('AI_NL_MODEL','TEST_ONLY');monkeypatch.setenv('OPENAI_API_KEY','TEST_ONLY')
    ai.cache.clear();ai.recent.clear()
    for key in ai.stats:ai.stats[key]='not_called' if key=='last_status' else 0
    async def denied(*args):raise ai.provider_failure(429,json.dumps({'error':{'code':code,'message':'TEST_ONLY_PRIVATE_KEY'}}))
    monkeypatch.setattr(ai,'_send',denied)
    result=asyncio.run(ai.propose_with_ai('TEST ONLY'))
    assert result['engine']['status']=='quota_exceeded'
    assert result['engine']['diagnostic']['error_code']==code
    assert result['period']['status']=='absent' and '반복 재시도로 해결되지 않습니다' in result['messages'][0]
    assert 'TEST_ONLY_PRIVATE_KEY' not in json.dumps(result)

@pytest.mark.parametrize('code,expected',[('rate_limit_exceeded','rate_limit_exceeded'),('slow_down','slow_down'),('TEST_ONLY_SECRET_CODE',None)])
def test_error_code_allowlist_and_bounded_wait(code,expected):
    result=ai.provider_failure(429,json.dumps({'error':{'code':code}}),'30')
    assert result.code==expected and result.retry_after==30
    for invalid in ['999999999999','-1','0','nan','Bearer TEST_ONLY']:
        assert ai.provider_failure(429,b'not json',invalid).retry_after is None

@pytest.mark.parametrize('body',[b'not-json',b'[]',b'{"error":null}',b'{"error":{"code":["bad"]}}'])
def test_unknown_429_does_not_become_claimed_billing_issue(body):
    result=ai.provider_failure(429,body)
    assert result.status==429 and result.code is None

def test_send_retains_http_status_for_oversized_error_and_strips_message(monkeypatch):
    original=httpx.AsyncClient
    bodies=[json.dumps({'error':{'code':'insufficient_quota','message':'TEST_ONLY_PRIVATE'}}).encode(),b'x'*70000]
    for body in bodies:
        transport=httpx.MockTransport(lambda request:httpx.Response(429,content=body,headers={'retry-after':'5'}))
        monkeypatch.setattr(ai.httpx,'AsyncClient',lambda **kwargs:original(transport=transport,**kwargs))
        with pytest.raises(ai.ProviderError) as raised:asyncio.run(transport_send({},'TEST_ONLY'))
        assert raised.value.status==429
        assert raised.value.code==('insufficient_quota' if len(body)<65536 else None)
