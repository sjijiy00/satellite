import asyncio
import pytest
from app import ai_interpretation as ai
from test_ai_interpretation import envelope,VALID,TEXT

def test_configured_limits_reach_transport_and_public_config(monkeypatch):
    for key,value in {'AI_NL_ENABLED':'1','AI_NL_PROVIDER':'openai','AI_NL_MODEL':'TEST_ONLY','OPENAI_API_KEY':'TEST_ONLY','AI_NL_TIMEOUT_SECONDS':'45','AI_NL_MAX_OUTPUT_TOKENS':'4000','AI_NL_REQUESTS_PER_MINUTE':'3','AI_NL_REQUESTS_PER_PROCESS':'9'}.items():monkeypatch.setenv(key,value)
    ai.cache.clear();ai.recent.clear()
    for k in ai.stats:ai.stats[k]='not_called' if k=='last_status' else 0
    sent=[]
    async def fake(payload,key):sent.append(payload);return envelope(VALID)
    monkeypatch.setattr(ai,'_send',fake)
    result=asyncio.run(ai.propose_with_ai(TEXT));assert result['engine']['status']=='succeeded'
    assert sent[0]['max_output_tokens']==4000
    assert ai.config()['limits']['timeout_seconds']==45
    ai.cache.clear();ai.stats['requests']=9
    assert asyncio.run(ai.propose_with_ai(TEXT))['engine']['status']=='limited'
    assert len(sent)==1

@pytest.mark.parametrize('raw,expected',[('invalid',12),('-5',10),('100000',90)])
def test_timeout_is_bounded(monkeypatch,raw,expected):
    monkeypatch.setenv('AI_NL_TIMEOUT_SECONDS',raw);assert ai.config()['limits']['timeout_seconds']==expected
