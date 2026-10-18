# Latest-repository integration and C4 closure retest

Recorded on2026-10-17, America/Los_Angeles. Following the request to use GitHub's latest version, fetch established `origin/main=5a68f12`; a separate `codex/c4-latest-integration` branch carried C4 configuration, provenance corrections and metric UI. The original demo/mac-integration directory and other terminals' in-flight edits were preserved. Main was not merged.

This supplements the version conclusions in [c4-handoff-closure](c4-handoff-closure-20261017.md). That record and its c784081 numerical results remain historical evidence; this report's exact baseline governs its newer B conclusions.

## Source and dependencies

- Repository: https://github.com/ChrisJiang123/harborguard; upstream baseline5a68f12, latest B implementation97a8c75.
- C4 commit6da0831, provenance closure7c96ae1 and metric summary6b18abb were applied in order to the independent branch. The newer frontend was already English; its language and newer functionality were preserved when resolving the metric-card conflict.
- Current package.json/package-lock and existing runtime/node_modules were reused, without upgrading/reinstalling dependencies. Build used installed Node22.23.1. Models, prompts, sampling and budgets were unchanged; no training.
- Independent workspace: /tmp/harborguard-b-review-20261017-codex. Environments/frozen data were reused through local paths only. No .env, whole dataset/model bundles or logs were committed. The delivery branch can be checked out in a normal directory.

## Provenance and metrics

The new workspace's provenance audit passed20/20. test50 remains40 contexts500+10 extra80 and matches the6da0831 recorded hash; the field-collected label was corrected. train501 matches Lenovo metadata: first493 training, last8 internal validation. Exact test50/confirm60 overlaps with training are0. Capture-batch/semantic-independence limits remain those of the [source audit](../acceptance_c4/data_provenance_20261017/README.md); no real-water performance claim is made.

| Synthetic set | Structure | IDs+facts | Option | Null | Mean generation latency |
| --- | --- | --- | --- | --- | --- |
| test50 | 50/50 | 44/50 | 31/33 | 14/14 | 3.75s |
| confirm60 | 60/60 | 39/60 | 35/36 | 18/18 | 4.71s |

Original metrics, complete-schema failure archives, independent denominators and configuration are preserved; the full LoRA evaluation was not rerun.

The sole B-generated fixture change was GET /api/metrics in `backend/fixtures/integration/backend.json`: its prior lora=null contradicted current published metrics. Only that response was synchronized; assertions, other examples and B algorithms were unchanged.

## Test results

- Full latest combination: **232 PASS,2 SKIP,0 FAIL**. Skips concern a separate COCO smoke weight; the official sonar YOLO was tested.
- C4/B safety focused tests:122 PASS; metric snapshot focused tests:4 PASS; frontend build and English check:PASS.
- First full run had35 setup errors because the requested temporary parent directory did not exist, plus the stale metric snapshot difference. Creating the isolated directory and updating that single response allowed a passing rerun. Initial failure logs were preserved; assertions were not altered to hide failures.
- Three complete600-simulation-second B runs kept all four hazard locations non-clear throughout, ending6clear/3blocked/3unsurveyed. Event/state/PNG semantic hashes matched across runs; reopening excluded hazards. The9h estimate is a demo quantity derived from current clear zones. Tests also covered original bad frames, near field, wrong class, low confidence and actual C multi-target projection.
- Offline numeric tests used CLOUD_PROVIDER=disabled and intercepted HTTP:0 call attempts.
- A rerun found L1=1.0,L2=150.7,L3=505.0s and first UUV363.9s. **The level-3-within500s requirement still FAILS.** Passing automated suites do not waive taskbook timing.

Latest B uses anonymous geometric observations, still synthetic sensor assumptions. Hazards absent from the observation stream, full tracking/AIS truth coupling, crowded crossing-contact association and real echo end-to-end perception are outside the passed scope. The original C terminal still owns the public projection helper; uncommitted geometry was not silently mixed into this remote baseline.

## Isolated local preview of this version

| Service | Isolated endpoint/configuration |
| --- | --- |
| Frontend | http://127.0.0.1:5174/ |
| Backend | http://127.0.0.1:8004, separate artifacts/latest-preview.sqlite3 |
| Agent | http://127.0.0.1:8002/health, harborguard-lora, draft_output_format=json, cloud disabled with0 calls |
| Ollama | Existing11434; warmup probes excluded from business generation latency |

Only the isolated8004 process added localhost5174 CORS and8002 Agent URL. Shared interfaces/default repository ports were unchanged. Original8000/8001/5173 were not restarted/replaced. Disabled cloud is an isolated test setting; the original demo health retained OpenRouter/google/gemini-2.5-flash → local LoRA → template.

An actual browser inspection confirmed the new English LIVE page, harborguard-lora/json, two synthetic origins, integer denominators and6/50,21/60 fact-failure notices. Original settings/history remained expandable. API200 was not substituted for UI acceptance. Screenshots/logs remain in the original runs/codex-c4-handoff/; hashes/machine summary are in [latest-integration.json](../acceptance_c4/data_provenance_20261017/latest-integration.json).

## Remaining ownership at this snapshot

- **B:**505-second timing; preserve old database during final cutover and use a separate one matching the new fingerprint.
- **A:** final-port browser recovery/endurance/field checks; uncommitted question-answer UI remains with its original terminal.
- **C:** commit/integrate public sonar geometry helper; actual qwen3→LoRA round-trip rollback had not yet run at this snapshot.
- Physical Wi-Fi loss, projector readability and cross-device playback await the owner. No public/Vercel deployment, main merge or force push occurred.
