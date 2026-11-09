"""No default test may spend an actual OpenAI credential."""
import pytest
from app import ai_interpretation as ai

@pytest.fixture(autouse=True)
def no_paid_ai(monkeypatch):
    async def forbidden(*args,**kwargs):raise RuntimeError('TEST ONLY: actual paid AI blocked')
    monkeypatch.setattr(ai,'_send',forbidden)
