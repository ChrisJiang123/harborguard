# HarborGuard Agent (C, port 8001)

**C3 implements four event triggers, deterministic fact checks and the OpenRouter → local Ollama → template route. Cloud use requires an explicit provider selection. Legacy Anthropic/Z.ai adapters are retained; existing credentials alone never enable them.**

```text
agent/
  config.py          # Explicit load_dotenv; configurable models, addresses and timeouts
  main.py            # FastAPI /health and /ask, WebSocket consumer and serial task queue
  context.py         # Deterministic REST context collection; UTF-8 size <= 3 KB
  factcheck.py        # Recomputable facts, option rules, uncertainty and evaluation boundaries
  prompts.py         # Shared system prompts for cloud, local generation and distillation
  router.py          # Cloud → Ollama → template, deadlines and statistics
  schemas.py         # Strict six-field Pydantic draft, allowed truncation and ID validation
  template.py        # Deterministic security/disaster/buoy recommendations and factual answers
  backend_client.py  # REST /api, WebSocket /ws, reconnect and since_seq compensation
```

## Start

Start B first (default `http://localhost:8000`), then run from the repository root:

```bash
source .venv/bin/activate
python -m agent.main  # Default: 127.0.0.1:8001
```

The Agent explicitly loads the root `.env`. Common settings are `BACKEND_BASE_URL`, `BACKEND_WS_URL`, `BACKEND_TIMEOUT_S`, `AGENT_HOST`, `AGENT_PORT`, `AGENT_EVENT_BUDGET_S`, `AGENT_CLOUD_BUDGET_S` and `AGENT_FAILURE_LOG`. `CLOUD_PROVIDER` defaults to `disabled`; legacy variables such as `ANTHROPIC_AUTH_TOKEN` cannot silently enable a cloud service. `BACKEND_BASE_URL` is the backend root; the client adds exactly one `/api` for REST. An empty `BACKEND_WS_URL` derives `/ws` from that root.

The documented OpenRouter configuration uses `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1` and fixed model `google/gemini-2.5-flash`. Recommendation generation uses `RecommendationDraft.model_json_schema()`, `response_format.type=json_schema`, `strict=true` and `provider.require_parameters=true`. Unsupported endpoints must fail rather than drop structure constraints. The SDK uses `max_retries=0` and `provider.allow_fallbacks=false`; the Agent's overall deadline controls fallback. Requests include `usage.include=true`. `/health` reports tokens, returned costs, upstream provider and actual response model only for requests already made; health checks do not make billable requests. Credentials come from `.env` or process environment and are excluded from logs.

The legacy `CLOUD_PROVIDER=anthropic` adapter can still be selected explicitly. Protocol compatibility does not establish that the upstream is Anthropic Claude. This acceptance round did not contact Z.ai. The documented demo-machine settings are `OLLAMA_MODEL=harborguard-lora` and `OLLAMA_FORMAT_OVERRIDES=harborguard-lora:json`. Unlisted models, including `qwen3:1.7b`, retain the complete schema. C0 uses the same adapter and reports the tested model/format instead of substituting another installed model.

## Language and validation

`AGENT_LANG=en|zh` defaults to `en` and controls recommendations and answers. English limits are 25 words for summary, 120 words for explanation and 15 words per uncertainty. Chinese mode retains 60/300/40 characters. Contract v1's 60/300/40 character limits still apply in both modes; English truncation prefers complete words. English templates use English class names rather than echoing Chinese option labels or arbitrary unknown class names.

The current LoRA was trained on Chinese distillation data. This change does not retrain it. In English mode, Chinese text in any model recommendation field is rejected before truncation and follows the existing retry/deadline route to an English `model=template` fallback; it is not counted as local-model success. `/ask` likewise rejects Chinese replies in English mode. Structure, IDs, facts, option rules and low-confidence checks remain enforced. English vocabulary conversion is limited to the fact-check view and changes neither returned text nor context IDs. Historical Chinese test50/confirm60 results require the frozen Chinese prompt; they are not English-language capability measurements.

```bash
curl http://127.0.0.1:8001/health
curl -X POST http://127.0.0.1:8001/ask \
  -H 'Content-Type: application/json' -d '{"question":"What is the current situation?"}'
.venv/bin/python -m pytest -q tests/test_agent_phase1.py tests/test_agent_phase2.py tests/test_agent_phase3.py
```

## Runtime flow

Events trigger REST collection of actual backend context, cloud/local/template draft generation, then Pydantic, context-ID and deterministic-fact validation. Valid recommendations are posted to `/api/recommendations` and broadcast by B as `recommendation`. Triggers are `options_ready`, `alert_changed` rising to level 2, `reopen_plan`, and `buoy_changed` becoming down. Initial connection and reconnect compensate via `since_seq`. Identical payloads are deduplicated. The same reopening plan is not resubmitted and is accepted at most once per 20 simulation seconds. Scenario reset/start clears payload deduplication, throttles and obsolete tasks.

The default event budget is 9.5 seconds, reserving 0.5 seconds for template fallback and POST; cloud generation can use at most 4 seconds. A returned draft with invalid structure, IDs or a demonstrable factual contradiction gets one retry with validation errors. Authentication, permission, connection and timeout failures fall back immediately. `state.network=offline` skips cloud calls entirely; `network_up` clears the cloud health breaker. Ollama startup records cold/warm probe times. Every generation await is cancelled at its deadline; late model results are never submitted after a template.

Fact checks cover offline buoy counts/IDs, coverage counts, detection confidence, option risk/delay, selection rules, absent options, null disaster/buoy recommendations and insufficient evidence. Negation is classified before matching, so a statement that no buoy is offline is not rejected merely for containing the offline term. Arbitrary free text is not claimed to be fully verified; `/health` declares the check scope. Failed-fact examples store only required facts and hashed IDs under ignored `agent/runtime/`; they are not automatically added to distillation data.

## Recorded C-team measurements (2026-10-17)

These measurements describe their recorded configurations; they do not establish that the current full demo or every model route has passed acceptance.

`GET /health` separates first-pass structure, first-pass facts, all raw outputs, retries, model successes, template fallback, tokens and returned costs. The OpenRouter structured probe took 2199.8 ms. Backend-triggered security/options_ready, buoy/down and disaster/reopen_plan took 2635.0, 5435.8 and 1874.2 ms; all three submitted `model=cloud`. An isolated 20-generation/POST run recorded 20/20 first-pass structure, 20/20 first-pass facts, cloud/local/template=20/0/0 and no retries. Generation-to-POST latency was median 1416.1 ms, P95 2086.0 ms and maximum 2264.2 ms. The API returned 23,498 tokens and $0.0129571; the cost is the observed response value, not a price-table estimate.

The recorded simulated-offline run made zero cloud calls and used local generation in 4707.6 ms; restored network used cloud in 2298.2 ms. Isolated invalid cloud credentials plus unreachable Ollama returned a template in 49.1 ms without changing real credentials. `/api/agent/ask` took 673.6 ms with `model=cloud`.

The hard boundary is unchanged: the Agent interprets and recommends; it never changes alert levels or calls `/api/decision`. Deterministic rules cannot validate arbitrary natural-language semantics. The boundary is exposed in `/health.fact_check_scope`.
