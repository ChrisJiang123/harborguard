"""C0 must use the configured model and runtime format, with no silent fallback."""
import asyncio
from dataclasses import replace
import httpx
import pytest
from agent.config import load_settings
from scripts.check_c0 import configured_local_chat


def test_c0_uses_configured_model_and_format(monkeypatch):
    captured=[]
    def handler(request):
        import json
        captured.append(json.loads(request.content))
        return httpx.Response(200,json={'model':'harborguard-lora:latest','message':{'content':'{"answer":2}'}})
    client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr('agent.router.httpx.AsyncClient',lambda **kw:client)
    cfg=replace(load_settings(),ollama_model='harborguard-lora',ollama_format_overrides='harborguard-lora:json')
    model,fmt,_=asyncio.run(configured_local_chat(cfg,['harborguard-base:latest','harborguard-lora:latest']))
    assert (model,fmt)==('harborguard-lora','json')
    assert captured[0]['model']=='harborguard-lora'
    assert captured[0]['format']=='json'
    assert captured[0]['think'] is False


def test_missing_configured_model_fails_instead_of_using_first_model():
    cfg=replace(load_settings(),ollama_model='missing')
    with pytest.raises(ValueError,match='not installed'):
        asyncio.run(configured_local_chat(cfg,['harborguard-base:latest']))
