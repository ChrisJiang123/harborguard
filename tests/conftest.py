"""pytest 根配置：把仓库根加入 sys.path，使 `import ml...` / `import agent...` 生效。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "agent_language(lang): language of legacy/output fixtures")


@pytest.fixture(autouse=True)
def explicit_fixture_language(request, monkeypatch):
    marker = request.node.get_closest_marker("agent_language")
    if marker:
        monkeypatch.setenv("AGENT_LANG", marker.args[0])
        import agent.config
        monkeypatch.setattr(agent.config, "_settings", None)
