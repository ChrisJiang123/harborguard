# Mac Local LIVE Demo Runbook

Historical instructions for the `demo/mac-integration` branch without query parameters. Formal ports: B 8000, Agent 8001, Ollama 11434 and production A preview 5173. `?mock=1` and Replay are explicitly offline fallbacks, not substitutes for real integration.

## Pre-demo checks

Run from repository root:

```bash
cd /Users/chrisjiang/Projects/harborguard
for port in 11434 8000 8001 5173; do
  echo "PORT ${port}"
  lsof -nP -iTCP:${port} -sTCP:LISTEN || true
done
curl -fsS http://127.0.0.1:11434/api/tags
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS http://127.0.0.1:8001/health
```

For an occupied port, inspect command, working directory and health. Reuse a confirmed healthy project service; do not terminate unknown processes. Formal preview uses 5173. If another project owns it, its owner must stop it normally. Other ports are diagnostic only and do not establish formal-port acceptance.

Local-only frontend/.env.local:

```dotenv
VITE_API_BASE=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

The root `.env` contains model credentials: never print it, copy it into logs or commit it. Recorded route: OpenRouter `google/gemini-2.5-flash` → Ollama `harborguard-lora` → deterministic template. `OLLAMA_FORMAT_OVERRIDES=harborguard-lora:json`; unlisted models retain the complete schema. Structure, ID, fact and option checks and the 9.5-second event budget are unchanged. Template fallback is not local-model success. Historical full-schema LoRA failures stay archived and are distinct from current JSON-format results.

[Provenance](../acceptance_c4/data_provenance_20261017/README.md): test50/confirm60 are synthetic, with factual passes 44/50 and 39/60, not real-water performance. The top-level health model is the last result; the configured model is `router.providers.local.request_model`. `warmup.cold_ms/hot_ms` are probes, not business-generation latency. An old process without `draft_output_format` cannot pass format verification merely by returning health 200. The added source field requires an owner-coordinated restart and JSON-format check. Do not interrupt another terminal just to check it.

For rollback, restore previous configuration or set `OLLAMA_MODEL=qwen3:1.7b`, clear the override, coordinate restart and check health; then restore LoRA. At this historical snapshot, default-behavior tests and a configuration backup existed, but **the actual qwen3→LoRA round trip had not been rehearsed**. Instructions are not a passing record. Later acceptance reports may record subsequent exercises.

## Startup order

Start a service only when its health fails and its port is free. Use separate foreground terminals and stop with Ctrl-C in the same terminal. Do not terminate processes in bulk by port.

```bash
# Terminal1
ollama serve
# Terminal2
cd /Users/chrisjiang/Projects/harborguard
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
# Terminal3
cd /Users/chrisjiang/Projects/harborguard
.venv/bin/python -m agent.main
# Terminal4
cd /Users/chrisjiang/Projects/harborguard/frontend
npm run build
npm run preview -- --host 127.0.0.1 --port 5173 --strictPort
```

Open http://localhost:5173/ without query parameters and confirm LIVE. If it fails, inspect 8000/WebSocket. Do not switch to mock and continue claiming live integration.

## Four-minute sequence

### 0:00–0:25: health/provenance

Show LIVE, health on all four ports and metrics. YOLO used 600 synthetic validation images, mAP50=0.9771, CPU approximately 50ms/image. Show `harborguard-lora/format=json`, independent test50/confirm60 denominators and factual limitations.

### 0:25–1:45: A

Start A at 10× and select an underwater target. Show 2D/3D position, history and escalation. Wait for an active-ping Detection, open its PNG and check `model=yolo26n` rather than stub. After `options_ready`, show the Agent recommendation. Call it cloud-generated only when the actual event says `model=cloud`.

Before approval, explain that advice has not automatically restricted zones. Select a current option, enter an operator and approve. Wait for B's `decision/zone_changed` evidence before claiming restriction. The Agent must not call `/api/decision`.

### 1:45–2:55: B — historical deployment warning

At this snapshot, the local demo had not adopted B's P0 fix: the 250m northern-anchorage contact was misclassified and then cleared; the 0m fuel contact was missed and then cleared; coverage erased unresolved observations; multi-target projection was wrong. Remote B passed three isolated real-weight runs with all four hazards never clear, but the local demo had not been switched. Do not claim that historical service was fixed or that 12h saved was an accepted safety result. With owner approval, show the actual `reopen_plan` and disaster recommendation with null option. A does not compute the plan.

### 2:55–3:35: simulated external-network fallback

Inject network offline, then buoy down to trigger new advice. LIVE stays connected and local images/3D remain available. Label the next recommendation as local/template according to its actual source. `network=offline` tests cloud skipping, not a physical Wi-Fi disconnect.

Restore network. Without a new actual cloud recommendation, claim only restored conditions, not a verified switch back.

### 3:35–4:00: metrics/limits

Check `/api/metrics`. YOLO is unchanged; LoRA factual passes remain test50=44/50 and confirm60=39/60, both synthetic. Three venue checks remain manual: actual Wi-Fi-off refresh, readability at three meters on the projector, and cross-device playback of the finished recording.

## Finish

Reset to idle. Preserve others' services; use Ctrl-C only in your own terminals, then verify those processes exited with the same port checks. Do not terminate unknown PIDs.

Before physical Wi-Fi loss, load all four local services/resources. Physical disconnection, projection and recording permission require the onsite operator; source checks cannot replace them.
