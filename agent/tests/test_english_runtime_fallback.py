"""English-mode service failure must remain understandable to the demo operator."""

import asyncio
import re

from agent import main


def test_ask_backend_failure_returns_english_template(monkeypatch):
    monkeypatch.setenv("AGENT_LANG", "en")

    async def unavailable():
        raise ConnectionError("isolated test backend unavailable")

    monkeypatch.setattr(main.client, "get_state", unavailable)
    response = asyncio.run(main.ask(main.AskBody(question="Current situation?")))

    assert response["model"] == "template"
    assert response["answer"]
    assert not re.search(r"[\u3400-\u9fff]", response["answer"])
    assert len(response["answer"]) <= 150
    assert "officer" in response["answer"].lower()
