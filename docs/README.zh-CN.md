<!-- English translation of the historical README from a4d4027. Legacy filename retained for stable links. -->

# HarborGuard C: historical environment and acceptance notes

This file is an **English translation of the archived Chinese README** from commit `a4d4027`. Its legacy filename is retained for incoming links. Historical claims below retain their original scope and dates; they do not supersede the [current README](../README.md), latest acceptance reports or current main SHA.

The 2026-10-17 full-system delivery check used main `a841bf9`: [results/limits](final-delivery-20261017.md), [five-minute runbook](demo-runbook.md), [Devpost draft](devpost-submission-draft.md). That Windows run used templates and completed a 2D browser loop in 4m46s; recovery boundaries and 3D still had failing/pending items. C-team measurements below are distinct from that combined run.

HarborGuard is a 24-hour underwater-security digital twin for the Port of Los Angeles. A serves the frontend on 5173, B the backend on 8000 and C the Agent/models. See [frontend instructions](../frontend/README.md) for current frontend/3D status and [Mac runbook](mac-demo-runbook.md) for four-process startup, port protection, shutdown and a four-minute live demonstration.

## C modules and frozen interfaces

| Directory | Task | Historical status |
| --- | --- | --- |
| `ml/sonar/` | C1 renderer and synthetic dataset | Implemented; 4,000 synthetic images; actual B renderer integration checked |
| `ml/yolo/` | C2 YOLO26, SonarDetector, metrics | Lenovo delivery accepted on Mac; synthetic-val mAP50 0.9771, CPU 49.7 ms/image; B emits `yolo26n` |
| `agent/` | C3 service/context/routing/question answering | OpenRouter → local → template; recorded 20/20 cloud submissions |
| `ml/lora/` | C4 distillation/LoRA/GGUF/Ollama | Lenovo training/export and Mac integration completed; JSON-format synthetic test50 facts 44/50, confirm60 39/60 |

The `render_ping`, `SonarDetector`, REST and Recommendation interfaces follow [shared-contract-v1.md](shared-contract-v1.md), maintained by B and frozen at H2. Names/signatures are unchanged.

## Separate environments

| Environment | Location | Purpose | Recorded platform |
| --- | --- | --- | --- |
| Runtime | Root `.venv` | Agent, renderer, CPU detector, self-check | MacBook, Python 3.11 |
| YOLO training | `.venv-yolo-train` / Colab | 50-epoch training | Lenovo Windows Python 3.12.10, cu130; Colab fallback |
| LoRA training | Lenovo/Windows | Unsloth + TRL SFT | Completed separately; runtime host only integrates/retests |

```bash
bash scripts/setup_env_runtime.sh
# Linux/bash training helper; this script itself was not validated:
PYTHON_VERSION=3.12 YOLO_CUDA_INDEX=cu130 bash scripts/setup_env_yolo_train.sh
```

Windows training uses the PowerShell notes in `requirements-yolo-train.txt`; the validated interpreter path uses `Scripts\python.exe`. See `requirements-lora-train.txt` and `ml/lora/README.md` for historical training setup. On the recorded macOS 26 machine, Homebrew Python returned an empty `platform.mac_ver()`, breaking pip/truststore. The runtime helper prefers uv (`brew install uv`); normal machines can use `python3.11 -m venv`.

## Configuration

`agent/config.py` explicitly calls `load_dotenv()`:

```bash
cp .env.example .env  # Fill credentials locally; .env is ignored and must not be committed.
```

The archived active configuration selected `CLOUD_PROVIDER=openrouter`, `OPENROUTER_MODEL=google/gemini-2.5-flash`, `OLLAMA_MODEL=harborguard-lora` and `OLLAMA_FORMAT_OVERRIDES=harborguard-lora:json`. Other local models retain the complete schema. Routing is OpenRouter → local LoRA → deterministic template. The Agent explains/recommends; only an operator invokes a decision. Historical C0/C3 routes do not establish the current machine configuration.

## C0: environment self-check (2026-10-16)

```bash
.venv/bin/python scripts/check_c0.py
```

The script reports PASS/FAIL/PENDING. Missing API key/GPU or a physical network-disconnection check is PENDING, never fabricated PASS. Automated checks and final acceptance are distinct; manual checks stay pending until their owner supplies results.

- Recorded automated checks: 10/10 PASS for Python 3.11, dependencies, Pydantic v2, yolo26n.pt, Ollama CLI/service, actual qwen3:1.7b conversation, one cloud call and explicit dotenv loading.
- Historical cloud configuration (credentials excluded): `https://api.z.ai/api/anthropic`, explicit process `ANTHROPIC_BASE_URL`/`ANTHROPIC_AUTH_TOKEN`, returned model `claude-sonnet-5`. This is a recorded response identifier, not a present provider identity guarantee.
- Manual Wi-Fi-off Ollama dialogue: **not verified**.
- Lenovo YOLO GPU check was owner-verified on 2026-10-16: Windows, Python 3.12.10, RTX 5060 Laptop GPU (8151 MiB, sm_120), torch 2.14.1+cu130, torchvision 0.29.1+cu130, ultralytics 8.4.178. CUDA operations/backprop and YOLO26 device=0 passed. These versions are historical measurements, not a newest-version claim; do not rebuild the validated environment.
- At this C0 snapshot, Colab/Unsloth LoRA GPU acceptance was unverified. Later C4 completion is recorded below.
- Reasoning models such as Sonnet 5/qwen3 can consume small token budgets before visible output; the self-check and C3 account for that.

## C1: synthetic renderer (2026-10-16/17)

Renderer, generator and preview passed 13/13 tests. Seed 0 generated 4,000 images in 31 s: 3,400 train/600 validation, 10.9% negatives, class-share deviation ≤0.1 percentage points, 8,935 generated objects/8,926 labels. Nine echoes below the contract's 16 px² threshold were discarded; no additional small-target filtering was applied. **All data is synthetic; these metrics are not real-sonar performance.**

Three layers of actual backend integration were recorded on 2026-10-17:

1. B's SonarClassifier called render_ping, returning a 640×640 sector PNG, byte-identical for the same seed, with accepted labels.
2. The merged B snapshot passed 73 backend tests.
3. Live Scenario A produced five detection events. `GET /api/sonar/det-5.png` returned the sector renderer output with B's detection box and “uuv 0.83” annotation. `model=stub` was the expected no-weights fallback.

`shared/contract.md` and `docs/shared-contract-v1.md` were compared: tables/types/signatures/IDs agreed; only headings/list formatting differed. `ml/sonar/samples.png` is a 4×4 preview. The 321 MB dataset is ignored and reproducible with `python -m ml.sonar.gen_dataset --n 4000 --seed 0`.

## C2: Mac acceptance of Lenovo delivery (2026-10-17)

SonarDetector loads weights once, forces CPU, converts grayscale to three channels and returns pixel bboxes. Missing weights raise FileNotFoundError; B can use an explicit stub, never fabricated detections. `ml/yolo/check_data.py` uses the actual Ultralytics dataset loader: 3,400/600 images, 435 negatives, class IDs 0–3 match the contract.

`ml/yolo/train.md` contains Lenovo PowerShell/Colab rerun and packaging commands. `eval.py` writes mAP50/mAP50-95/class recall/20-image mean CPU latency to metrics.json; missing weights fail without placeholder metrics.

The Mac acceptance in `ml/yolo/ACCEPTANCE-MAC.md` recalculated ZIP/best.pt SHA256 and the entire MANIFEST. Class order agreed in classes.json, portable_data.yaml and checkpoint names. On 600 synthetic validation images, mAP50 was **0.9771**, CPU **49.7 ms/image** (initial 52.1 ms), consistent with Lenovo. After B restart, detection det-5 used `model=yolo26n`, uuv confidence 0.72; `/api/metrics.yolo` exposed the Mac results. Real-sonar generalization and UATD-transfer gains were not compared or claimed.

## C3: Agent integration (2026-10-17)

- `python -m agent.main` serves /health and /ask on 8001; /ask uses cloud/local/template with an 18-second hard budget.
- The client subscribes to actual /ws and compensates initial/reconnected connections via /api/events?since_seq=. REST /api and WS /ws semantics are separate; sequence rollback after backend restart is supported.
- options_ready collects deterministic REST context, ≤3 KB UTF-8, validates Pydantic/context IDs and posts /api/recommendations; B broadcasts recommendation.
- Live/recovered overlap and identical processed option payloads are deduplicated. New metrics replace old jobs. alert_cleared and reset/start invalidate queued/in-flight old work.
- Shared prompts are retained in agent/prompts.py. Drafts require all six fields; invalid JSON, missing/extra fields, wrong types, empty text and illegal IDs fail. Only contract-allowed text truncation is permitted. Invalid output gets one error-guided retry.
- Event budget is 9.5 s with 0.5 s reserved for POST/template. SDK retries are disabled. Deadlines cancel awaits; generation and scene version are checked before submission.
- OpenRouter uses google/gemini-2.5-flash, strict json_schema and require_parameters, without provider fallback. An isolated run recorded **20/20 first-pass structure and facts, model=cloud**, detailed in agent/README.md.
- The earlier qwen3:1.7b baseline used explicit no-thinking and JSON Schema: 20 real POSTs, local/cloud/template=20/0/0, structure/IDs 20/20, mean 5.153 s, max 8.650 s. Those are **not** natural-language fact-pass rates.
- Historical isolated invalid cloud credentials/unreachable local returned a template in 398 ms without modifying/exposing real secrets. The Agent never changes levels or calls /api/decision.
- Deterministic checks cover buoy IDs/counts, coverage, confidence, risk/delay, option selection and insufficient evidence, including correct negation handling. /health distinguishes structure/facts/failures/retries/model/template.
- Level-2 alert_changed, reopen_plan and down buoy_changed triggers are implemented. Plans are payload-deduplicated and throttled to once per 20 simulation seconds; resets clear throttles/tasks.
- Recorded actual-backend timings: Scenario A level-2 template 9007.6 ms, buoy template 9002.6 ms, Scenario B local disaster recommendation 5136.3 ms. Disaster/buoy option IDs were null, evidence IDs came from B; generation followed by reset produced no late recommendation.
- Redacted fact-failure records go only to ignored agent/runtime/, never automatically into training. Rule checks do not establish arbitrary free-text truth.
- The old Z.ai 429 problem was bypassed by explicit OpenRouter selection; this round made no further paid probes to the old service.

## C4: distillation and LoRA (2026-10-17)

`gen_contexts.py` produces 500 synthetic contexts at seed 0 (plus 80 supplemental at seed 1), kind ratios 70/20/10. Weighted risk, option ordering and factcheck.security_selection agree; IDs come from B1–B10/zones/assets; each context goes through C3 _trim ≤3 KB. Buoy-loss coverage is recomputed from actual scenario geometry and locked by tests.

`capture_real.py` ran local B scenarios A/B three times, including network/noise/buoy faults, and captured 51 unique runtime contexts: security 23, disaster 21, buoy 7, including 12 offline. Obsolete-session alerts were dropped. **“Real context” here means a running simulation backend, not a physical sonar or real-water collection.**

`distill.py` uses the same OpenRouter teacher/system prompt and structure/ID/fact validators as C3, at concurrency eight. Invalid outputs get an error-guided retry, then one teacher-only format hint. Hints never enter stored standard three-message training examples. The recorded pass rate was **95.2%**, total cost approximately **$0.50**. Cache keys use the exact runtime serialization SHA256; already-valid samples are never requested again. Seed-0 synthetic split is fixed at 450/50; 51 runtime contexts append to training only. Final input is **501 train/50 test**. A script/AI spot check of 30 found correct options/no invented IDs/concise Chinese; owner manual review remained pending.

`train_lora.ipynb` uses Colab Unsloth/TRL SFT, rank16/alpha32/lr2e-4/3 epochs/max_len4096/bf16 without 4-bit training. Candidate bases were Qwen3.5-0.8B → Qwen3-1.7B → 0.6B, falling back only when a model does not exist. Other failures stop. Actual model/revision/precision/parameters/token audit are recorded in training_meta.json. Precision is bf16 when supported, otherwise mutually exclusive fp16. Token audit asserts no truncated assistant answers. Eight trailing training records form internal validation; test.jsonl never enters training. Loss applies to assistant spans only; export is q4_k_m GGUF. Modelfile uses local harborguard.gguf, temperature0.2 and request-supplied system prompt.

`eval.py` serially compares paired untuned base and LoRA using the same base/quantization/chat template/inference parameters. qwen3:1.7b is a separate system_baseline; its model-size difference cannot be attributed to fine-tuning. Metrics separate first/retry structure, ID+facts, option agreement with denominator, disaster/buoy null correctness and latency including failed attempts. There is no template fallback in evaluation; failures stay in denominators. metrics.json is written only with a complete paired comparison.

The historical qwen3:1.7b system baseline measured 100%/100% structure, **16% ID+facts**, 45.5% option agreement (n=33), about9.9 s/sample. Schema-constrained structure success did not establish factual correctness.

Lenovo training/GGUF export and Mac switch were later completed; original complete-schema failures remain as evidence. JSON-format test50 measured structure50/50, facts44/50, options31/33, null14/14, mean3.75 s. Confirm60 measured structure60/60, facts39/60, options35/36, null18/18, mean4.71 s. **Both are synthetic-context evaluations.** test50 can be rebuilt in order from valid synthetic distillation; the earlier “field-collected test set” label was wrong. The ordered 501 inputs split into 493 train (450 synthetic +43 runtime captures) and8 internal validation. See [C4 provenance audit](../acceptance_c4/data_provenance_20261017/README.md) for hashes/origins/duplicates.

At this historical snapshot, actual qwen3↔LoRA rollback, physical Wi-Fi loss, projection and cross-device playback awaited owner confirmation. B's remote P0 fix had three isolated real-weight retests but was not yet the current demo combination. Two historical integration timing failures remained unresolved pending B/A final integration.

## Ignored files and A/B startup

Ignored: .env, .venv*/, datasets, redacted agent/runtime/, runs/, logs and model .pt/.pth/.gguf. The explicit exception is final nano `ml/yolo/weights/best.pt`, a few MB.

A is under frontend/; B under backend/ and data/. Their own READMEs are authoritative for their modules. C notes here are historical.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
make backend
# make test; make record
```

Windows: `./dev.ps1 setup` then `./dev.ps1 backend`. B uses8000, ws://localhost:8000/ws and http://localhost:8000/docs. In another terminal, cd frontend, npm.cmd install, npm.cmd run dev. Open localhost:5173, or use ?mock=1 / ?replay=demo_full.jsonl without B. A6 remained pending physical projection, offline refresh and cross-device video playback.

Shared contract v1 remains in shared/ and docs/shared-contract-v1.md. B recordings are frontend/public/replay_a.jsonl and replay_b.jsonl; associated images live in replay_assets/. Old recordings remain explicitly labeled and are not evidence of the latest live model.
