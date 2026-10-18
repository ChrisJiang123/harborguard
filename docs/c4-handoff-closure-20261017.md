# C4 handoff closure (2026-10-17, America/Los_Angeles)

This inspection used local `demo/mac-integration`, inherited HEAD `6da0831`. No applicable AGENTS.md was found. After the first fetch, its remote branch was `46f6b16` (local ahead by1); remote main was `c784081`, with4/26 unique commits relative to inherited HEAD. The old report therefore did not justify a direct merge. This round did not merge main, switch the active branch, retrain/overwrite weights, rebuild environments, restart services, modify databases or deploy publicly. The original delivery response records its exact delivery SHA/push state.

## Provenance and reproducible chain

The earlier description of test50 as field-collected capture_real data was wrong and has been withdrawn. Original metric values remain unchanged.

1. Read-only regeneration of contexts500/seed0, extra80/seed1 and confirm60/seed424242 matched every context.
2. Of580 synthetic source contexts,552 had valid distilled outputs. Sorting by key and shuffling with seed0 yielded the first50 as test50 (40+10), then450 synthetic training records. Content and order were reproduced. Another52 valid synthetic records were outside these two splits.
3. The51 capture_real records occur only at the end of train. train501 SHA256 matches Lenovo training_meta. In original delivery order,493 actual training records are450 synthetic+43 runtime captures; all8 internal validation records are captures.
4. test50/confirm60 hashes match metrics at inherited6da0831; no changed test set was found. The confirm60 wrapper changes user-JSON whitespace only: normalized content/order matches the original60. Frozen files were not edited.
5. Exact-context intersections are0 for train501/test50, train501/confirm60, test50/confirm60 and real51/test50. Neither test set has internal exact duplicates. No overlap requiring a new frozen set was found. Prompts, parameters and checkpoints were not tuned.

Runtime capture means a **local simulation backend**, not physical sonar or real-water collection. Missing per-record capture-run IDs prevent reconstructing boundaries of the reported three runs from source alone. Exact deduplication does not prove semantic independence. Current hashes cannot independently prove historical creation times; pre/post-freeze timelines remain attributed to existing records. Do not claim an independent field-collected test result.

See the [provenance audit](../acceptance_c4/data_provenance_20261017/README.md) and [audit.json](../acceptance_c4/data_provenance_20261017/audit.json) for the script,20 checks, hashes and delivery-evidence index. Original datasets/models/detailed logs remain local rather than being committed wholesale.

## Retained evaluation results

| Synthetic context set | Structure | IDs+deterministic facts | Option agreement | Null | Mean/sample, including retry |
| --- | --- | --- | --- | --- | --- |
| test50 | 50/50 | 44/50 | 31/33 | 14/14 | 3.75s |
| confirm60 | 60/60 | 39/60 | 35/36 | 18/18 | 4.71s |

Integer numerators are uniquely recoverable from the original three-decimal aggregates and known denominators. Original results are unchanged; the two sets are not pooled.

Evaluation used json, temperature0/seed0/num_predict450/think=false, first attempt+one validation retry,30-second per-call timeout; warmup excluded. This does not guarantee the online9.5-second event budget. No template fallback was used and failures remain in denominators. Unlisted models retain complete schema. Complete-schema failures, archives and original model comparisons are preserved. A metric-publication bug that overwrote the original failure archive on repeated publishing was fixed; two successive publications in an isolated fixture verified archive preservation.

## Runtime integration and validation scope

- Processes on8000/8001/5173 belonged to this project;11434 was existing Ollama. They were reused without restart or business POST.
- 8001/health showed service=agent, local.request_model=harborguard-lora and cloud=openrouter/google/gemini-2.5-flash. Top-level model=template identified the last route result, not the configured model.
- The configuration file selected harborguard-lora:json, but the older running process did not expose draft_output_format. **Online format-field verification awaited a coordinated restart.** Health observability was added to source and json/default-schema paths tested. The [safe runtime snapshot](../acceptance_c4/data_provenance_20261017/runtime-check.json) contains allowlisted configuration only.
- Preserved pre-switch event evidence showed3 successful local recommendations,1 fact-failure template fallback,0 late POST after reset, cloud disabled. This round read that evidence without rerunning the complete LoRA experiment or counting templates as model successes.
- C offline tests:86 PASS; archive-preservation regression:1 PASS. Child processes explicitly used CLOUD_PROVIDER=disabled.
- Frontend build:PASS. Existing Node20.18.0 produced a Vite compatibility warning; the environment was not upgraded/rebuilt.
- An actual5173 LIVE browser inspection expanded the metrics UI and displayed model/format, two synthetic origins, denominators50/50 and60/60, facts44/50 and39/60, option31/33 and35/36, null and latency. It highlighted6/50 and21/60 fact failures. Original configuration/failure history remained expandable. Evidence: `runs/codex-c4-handoff/ui-{test50,confirm60}.png` and `ui-ax.txt`.
- No actual qwen3→LoRA round-trip rollback was run here: only default-path tests, a pre-switch backup and earlier forward switch existed. Physical Wi-Fi loss, projector readability and cross-device playback remained owner acceptance. The Agent never approves decisions.

## Isolated retest of remote B fixes

B implementation6353421 was already pushed and in remote main. A separate detached checkout at c784081 reused the existing .venv without services, demo database access, merging into the active workspace or loading uncommitted C geometry work.

- Final weights matched the current workspace SHA256: `2cad3146fa4b98516efa0057367c3c5d53220dc2a3246058f5608094a6568839`.
- B safety:16 PASS,0 SKIP. Three real-weight B runs continuously checked all four obstacle zones never became clear: all passed. Final6clear/3blocked/3unsurveyed,9h; event/state/PNG semantic hashes matched across runs. berth_fuel stayed unsurveyed; anchorage_north and two confirmed debris zones were blocked; reopening excluded hazards.
- Cloud was explicitly disabled and httpx sending intercepted: actual HTTP attempts0. No paid service or LoRA was called.
- A separate read-only Scenario A timing check found L1=1.0,L2=150.7,L3=505.0s, first UUV363.9s: **the500-second limit FAILS**. No assertion was relaxed and neither historical integration timing failure was waived.
- This establishes numerical safety only for that exact remote B/committed C combination on synthetic images. It does not establish that the current demo process was updated, full browser/endurance/real-water acceptance or all multi-target cases.

See [summary/raw-evidence hashes](../acceptance_c4/data_provenance_20261017/remote-b-check.json). Raw A/B results remain in runs/codex-c4-handoff/. [verify_remote_b.py](../acceptance_c4/data_provenance_20261017/verify_remote_b.py) reruns the three B checks against a supplied independent checkout.

## Ownership and remaining work at this snapshot

C provenance/config observability and frontend metric presentation were committed separately; only this round's runbook paragraphs were staged. Other terminals' backend/README, frontend/README, AgentCard, index.css, demo.sh, integration reports and C render/geometry tests/docs remained outside these commits.

- **B:** integrate the pushed safety fix into demo, preserve the old database and use a separate database for the new configuration fingerprint; investigate505-second timing.
- **A:** final combined browser acceptance after the pushed frontend update; in-flight question-answer UI remains owned by its original terminal.
- **C:** original terminal commits geometry helpers; coordinate restart to verify health format, then schedule actual rollback exercise.
- Final combination still needs timing, browser recovery, endurance and owner field confirmation. C4 metadata closure does not substitute for these.
