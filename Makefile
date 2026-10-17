ifeq ($(OS),Windows_NT)
PYTHON ?= .venv/Scripts/python.exe
else
PYTHON ?= .venv/bin/python
endif

.PHONY: backend test record samples check
backend:
	$(PYTHON) -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

test:
	$(PYTHON) -m pytest -q

samples:
	$(PYTHON) -m backend.tools.make_samples

record:
	$(PYTHON) -m backend.tools.record --scenario a --speed 10 --out frontend/public/replay_a.jsonl
	$(PYTHON) -m backend.tools.record --scenario b --speed 10 --out frontend/public/replay_b.jsonl

check:
	$(PYTHON) -m compileall -q backend
	$(PYTHON) -m ruff check backend
