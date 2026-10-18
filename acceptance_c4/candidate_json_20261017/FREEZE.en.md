# Candidate configuration freeze (2026-10-17)

English companion to [FREEZE.md](FREEZE.md). The original is retained byte for
byte because its SHA256 is part of the provenance audit. This translation does
not create a new freeze, rerun evaluations, or change the recorded chronology.

- Frozen scope: the `OLLAMA_FORMAT_OVERRIDES` mechanism (`frozen_config.diff`)
  and candidate value `harborguard-lora:json,harborguard-base:json`.
  `qwen3:1.7b` is absent from the table and therefore retains the full schema.
- Freeze evidence: dev9 (9 training examples), confirmed through the real
  evaluation path in `frozen_dev9_confirm.json`: LoRA structural validity
  100% / 100%, IDs and facts 89% / 89%, option consistency 100% (n=3), null
  handling 100% (n=6), and 2.09 seconds per example.
- Unit verification: `test_format_overrides.py`, 6/6 PASS. An empty default
  preserves the existing full-schema behavior; explicit overrides take effect;
  invalid values raise an error.
- After the freeze: evaluate all three model variants on the frozen 50-example
  test set. Do not tune prompts, parameters or checkpoints based on its results.
- Rollback: clear `OLLAMA_FORMAT_OVERRIDES`. The default code path is identical
  to C3.

## Additional freeze record (generated 2026-10-17 15:36; recorded 15:48)

- Confirmation set: `confirm_contexts_seed424242_n60.jsonl`, generated with
  `gen_contexts --n 60 --seed 424242`, including fault injection. The evaluation
  wrapper `confirm60.eval.jsonl` has SHA256
  `d6360787f9bda3d828bd2cdb0ac3990da63cf4793b210a28867f71f239e9aa28`.
- Timeline: this set was generated before the candidate's 50-example evaluation
  finished (15:36 < 15:47). It was not used for diagnosis or tuning.
- Provenance correction: the 50-example test set also contains synthetic
  contexts from `gen_contexts.py`. Its exact content and order can be rebuilt
  from 552 eligible synthetic distillation records using `split_records(seed=0)`.
  It was not collected by `capture_real`. The confirm60 set is a separate
  synthetic confirmation set using `seed=424242`, with zero exact duplicates
  against test50. Keep the independent integer denominators for both sets;
  neither result demonstrates generalization to real marine operations. See
  `acceptance_c4/data_provenance_20261017/`.
- Lenovo key-order materials were retested with byte fidelity confirmed.
  Both success/failure orderings were cycled on dev2 with Mac/Ollama. Only
  `format=json` passed. The key-order mechanism was not reachable on the Mac
  runtime, so the candidate remained on `format=json`.
