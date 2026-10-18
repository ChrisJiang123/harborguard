# ml/lora — Distillation and Local LoRA (C4)

The Ollama model harborguard-lora can serve Agent recommendations offline. The teacher uses C3's prompt and the same structural, ID, and deterministic-fact checks; local routing/request formats match C3 runtime. This document describes C's separate pipeline/evidence, not automatic acceptance of this route in every final demo.

## Separate environments

- Formal training finished on Lenovo/Windows. Mac performs GGUF/Ollama integration/evaluation only; no retraining in this round. Reproducible notebook: train_lora.ipynb; dependencies: requirements-lora-train.txt.
- Base: small Qwen3.5, initially 0.8B (actual model name follows Unsloth documentation). Notebook candidate fallback chain supports Qwen3 1.7B/0.6B if incompatible, matching local qwen3:1.7b.
- bf16 LoRA: rank 16, alpha 32, lr 2e-4, 3 epochs, max_len 4096. No 4-bit training.

## Reproducible pipeline; datasets/ is gitignored

| Step | Command | Output |
| --- | --- | --- |
| Synthetic contexts | python -m ml.lora.gen_contexts --n 500 --seed 0 | datasets/contexts.jsonl: 500 entries; kind 70/20/10; <=3 KB; weighted risk; taskbook-ranked options; actual B1–B10/zone/asset IDs |
| Runtime contexts | While B runs: python -m ml.lora.capture_real --seconds 235 | datasets/real_contexts.jsonl; C3 triggers, key-deduplicated append |
| Cloud distillation | python -m ml.lora.distill; 8 concurrent requests; --limit smoke, --retry-failed | datasets/distilled.jsonl with metadata; distill_failures.jsonl |
| Supplement | python -m ml.lora.distill --contexts datasets/real_contexts.jsonl --append-train | Only new contexts distilled and appended to training, preserving synthetic test baseline |
| Colab training | Upload train.jsonl, run train_lora.ipynb | Paired same-quantization harborguard.gguf/harborguard-base.gguf; adapter/tokenizer; training_meta.json with actual model ID/revision/precision/hyperparameters/token audit |
| Deployment | cd ml/lora && ollama create harborguard-lora -f Modelfile && ollama create harborguard-base -f Modelfile.base | Paired harborguard-lora and harborguard-base |
| Comparison | python -m ml.lora.eval; --skip-lora for system baseline only | metrics.json, exposed as B /api/metrics lora |

## Recorded status (2026-10-17)

- Generator/distillation/capture/evaluation scripts and tests/test_lora_*.py implemented.
- 501 training-pool entries: 450 synthetic (exact 450/50 split, seed 0) + 51 runtime contexts appended to training only. Synthetic test50 is fixed and excluded from training/prompt changes.
- Lenovo divided these in file order into 493 formal training entries and 8 internal validation entries: 450 synthetic +43 runtime training, 8 runtime validation. Independent test50 had zero exact overlaps with either.
- OpenRouter gemini-2.5-flash structured-output teacher: synthetic 552/580=95.2% accepted; runtime 51/51=100%; actual total cost ~$0.55.
- Runtime contexts: 51, comprising security23/disaster21/buoy7; 12 network-offline contexts from actual fault injection into the local simulated backend; A/B ran three rounds.
- System baseline qwen3:1.7b+prompt, serial test50 with one retry, retested 2026-10-17: structure 100%/100% first/after retry, ID+facts 16%/16%, option agreement45.5% (n33), correct null100% (n14), ~9.9 s/entry. Structural validity mainly comes from Ollama json_schema, matching C3; only16% passed complete deterministic facts (offline counts/IDs, coverage, confidence, option rules). Old json_valid=0.96 measured structure+IDs only and hid the fact gap. This is a system baseline; attributing benefit to 0.8B LoRA requires its paired untuned base with same quantization/template/settings. Different base sizes are not a fine-tuning comparison.
- AI/script spot-check of30 distilled entries: all matched ranked[0] or null, no fabricated IDs, concise Chinese summary<=60/explanation<=300. Human review remained pending owner confirmation.
- metrics.json format=json test50: structure50/50, facts44/50, option31/33, null14/14, mean3.75 s. Independent confirm60: structure60/60, facts39/60, option35/36, null18/18, mean4.71 s. Both use synthetic contexts and do not establish real-sea effectiveness.

## Design

- Training/runtime distributions align: standard system/user/assistant messages, user bytes serialized exactly like agent.router.generate (sort_keys and compact separators). GUIDED_HINT appears only in teacher retries, never in stored samples.
- Idempotency key is SHA256 of router-equivalent serialization. Previously accepted and recorded failed contexts are skipped to avoid duplicate requests.
- Validation uses parse_model_draft (structure/existing IDs) plus check_draft_facts (offline buoys, coverage, confidence, option rules). At most two retries, with format guidance on the second retry; record failure only after all three attempts fail.
- split_records deterministically creates450/50 with seed0. Runtime supplements enter training only via --append-train; base/LoRA always use the same fixed test.

## Runtime-context collection (2026-10-17 local simulation)

A at10× and B ran three rounds; one injected network_down/up, noise_up, buoy_down B2. capture_real received options_ready/alert_changed/reopen_plan/buoy_changed and captured51 unique contexts (23/21/7;12 offline), using C3 collect_* paths and UTF-8 <=3 KB. Repeated seeded events are key-deduplicated. Expired cached alerts from old sessions were dropped (HTTPStatusError39/36/36), not stored.

## Deployment/fallback notes (2026-10-17 C4 format=json candidate)

At that snapshot .env selected OLLAMA_MODEL=harborguard-lora and OLLAMA_FORMAT_OVERRIDES=harborguard-lora:json. Full-schema grammar decoding looped without termination on Mac/Ollama; see metrics.json history_schema_mode. This model therefore uses format=json; unlisted models such as qwen3:1.7b retain full schema.

Fallback: set OLLAMA_MODEL=qwen3:1.7b, clear OLLAMA_FORMAT_OVERRIDES, restart python -m agent.main, check :8001/health. Unit coverage/config backup exist, but an actual qwen3→LoRA round trip was not rehearsed and must not be called verified. Future native llama.cpp deployment must preserve Pydantic declaration order in schema, without sorted keys.

## Provenance audit addendum (2026-10-17)

See [audit scripts and per-file SHA256](../../acceptance_c4/data_provenance_20261017/README.md). test50 reconstructs in order from synthetic distilled records. The old “capture_real real test” label was incorrect; no test replacement or exact context overlap with training inputs was found. confirm60 likewise had zero exact overlap with training/test50.

capture_real captures the local simulation backend, not physical sonar. Missing per-record capture-run IDs prevent proving three batch boundaries from the file alone. Exact deduplication is not semantic independence. Original metrics and full-schema failure archives are retained. No retraining, retuning, or full model reevaluation was performed by this audit.
