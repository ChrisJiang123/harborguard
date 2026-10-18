# English repository presentation and preserved originals

Translation began at main `d2d4c6fbdff72de5b2d2c02aab0c39723513f3a8`.
Feature branch: `codex/harborguard-english-live`.

Latest main `07f42a21f30e9aad8a79369362abc5fe09f43744` (PR #21) was subsequently merged **into this feature
branch**, retaining the team's Vercel/Mac-tunnel/CORS preparation. Main itself
was not changed by this task. Final source comparisons use that newer main;
the initial 255-pass/2-skip regression belongs to the earlier translation
commit `4361210`. The audit records the separate rerun after PR #21.

Final preparation moved to `D:\HarborGuard-delivery\20261017-live3d-english\repo`
to use available D: storage. C: originals were retained. The capture itself
still belongs to the explicitly recorded earlier source and was not relabeled.

The final D:-drive regression after PR #21 is **259 passed, 2 skipped in
125.75 seconds**. The two skips lack optional cached COCO smoke weights; the
delivered sonar model was exercised. Frontend build, lint and the new deployment
configuration check pass. The earlier A1-A6/English/recovery checks also pass;
the frontend application source is unchanged between those baselines.

The project owner approved translating documentation, comments, interface copy
and normal runtime output while preserving original data and evidence. This is
an English presentation update, not a new algorithm, model or API version.

## Changed scope

- Translate current READMEs, runbooks, handoffs and historical report prose.
  Historical results keep their source SHAs, dates, measurements, FAIL/PENDING
  status and limits; translation is not a new acceptance run.
- Translate Python comments/docstrings and ordinary B/C logs, option display
  labels, operator-facing fallback text and offline CLI help/messages.
- Keep configuration values, model prompts, weights, generated input contexts,
  classification and approval logic unchanged. Config comments are English.
- Keep A's production source byte-identical. Frontend changes are documentation
  only; existing English UI and legacy source-text lookups are reused.
- Update the A3 poster, project story and Twist copy to use a real event-rich 3D
  simulation capture, with source records and explicit synthetic-data labels.
- Add an offline regression for an English Agent response when B is unavailable.

Production Python AST structure was compared after removing docstrings and
normalizing display strings. The fixture exporter has one explicit compatibility
adapter to reproduce the byte-identical original Chinese integration fixture;
it does not change the live service. Existing message assertions were updated
only for equivalent English text, without removing conditions or thresholds.

## Preserved Chinese and why it remains

| Original material | Reason and English access |
| --- | --- |
| `shared/contract.md`, `docs/shared-contract-v1.md`, shared/consumer TypeScript definitions | Frozen contract and exact copies stay unchanged. Use the [English reading guide](contract-reading-guide-en.md) and [REST/WS handoff](frontend-integration.md). |
| C4 `FREEZE.md` and formal `FINAL_REPORT.md` | Their hashes are audited. Separate `.en.md` companions translate them without rewriting the originals. |
| Raw JSON evidence, metrics, original model replies and JSONL replay | Preserve measurements, failures, hashes and reproducibility. English reports explain them; no old evidence is relabeled as a new run. |
| Original synthetic maps/assets/scenario names and their generators | Preserve the canonical data pack. The existing presentation lookup displays English without changing IDs or source records. |
| Chinese test inputs, expected vocabulary and legacy-language fixtures | Preserve multilingual coverage and actual test meaning. Original input literals are not replaced to make an English-only test pass. |
| Chinese Agent mode, teacher prompts and internal fact-check/retry vocabulary | Preserve model/evaluation behavior and deterministic validation. English is the default normal output, while deliberate Chinese mode remains available. |
| Training notebook and frozen experiment/reproduction scripts | Preserve experiment provenance; this task did not retrain or rerun the archived experiments. |
| Frontend translation lookup keys | Existing Chinese records need these keys to render in English. Removing them would break history display. |

Some internal validation details or arbitrary upstream diagnostic text may still
contain Chinese. This task does **not** claim every possible free-text error or
model reply has been translated. Normal Agent route/submission logs and its
backend-unavailable answer are English. Preserved vocabulary is not silently
rewritten because it can participate in validation and model retry behavior.

Only four tracked Markdown originals retain Chinese: the two frozen contracts
and the two hash-audited C4 reports. They have an English guide or companion.
The machine-readable [audit](english-translation-audit.json) lists every remaining
Han-bearing original, its reason and immutable-original SHA-256 checks.

## Verification

The final audit records exact test totals, durations and remaining-source counts.
It verifies original shared contracts, A production source, source data, replay,
fixtures, raw evidence and delivered weights against the baseline byte for byte.
For Git text files, the baseline comparison uses the repository's existing
checkout/EOL rules; both repository-blob and Windows-checkout hashes are recorded.
No original was rewritten to normalize line endings or bypass a fingerprint.

Commands used from the repository root with the prepared CPU environment:

```powershell
$env:CLOUD_PROVIDER='disabled'
$env:DEBUG_TRUTH_TRACKS='0'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
.venv/Scripts/python.exe -m pytest backend/tests agent/tests tests -q `
  --basetemp artifacts/english-live/pytest-frozen-temp `
  --junitxml artifacts/english-live/pytest-frozen.xml
.venv/Scripts/python.exe -m ruff check backend agent/tests/test_english_runtime_fallback.py
.venv/Scripts/python.exe -m compileall -q backend agent ml scripts tests
.venv/Scripts/python.exe -m pip check
```

The local verification reused an already prepared, compatible CPU virtual
environment at another worktree; it did not replace repository dependencies.
A fresh C:-local pytest temp directory avoids the existing cross-drive relative
path limitation of some C evaluation tests on this Windows host.

Frontend build, lint, A1-A6, English display and recovery checks were rerun.
The existing approximately 1.04 MB lazy 3D chunk warning remains. Existing C and
test lint findings were compared with baseline and were not silently fixed as
part of a translation; backend and the new regression pass Ruff.

Generated context packs `500/seed 0`, `80/seed 1`, `60/seed 424242` remain identical
to the original implementation. No LoRA training, model download, cloud request
or actual marine sensing is established by these checks.

For the captured simulation, actual REST/WS/Pydantic and PNG verification is in
[capture evidence](poster-live/evidence.json). A single event-rich 3D frame does
not replace full frontend recovery acceptance, 3D endurance, a recorded Demo
Video or a Devpost submission. No merge or force push is authorized by this file.
