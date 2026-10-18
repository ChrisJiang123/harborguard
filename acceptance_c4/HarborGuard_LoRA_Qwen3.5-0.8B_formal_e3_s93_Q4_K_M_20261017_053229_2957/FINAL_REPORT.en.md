# HarborGuard LoRA formal training results

English companion to [FINAL_REPORT.md](FINAL_REPORT.md). The original is
preserved byte for byte because its SHA256 is recorded in the provenance audit.
This is a translation of the existing training record, not a new training run
or a new acceptance result.

Completed at `2026-10-17T05:44:24.395707-07:00`: 3 epochs and 93 optimizer
steps. Training took approximately 9.55 minutes; loading and export brought the
total to approximately 11.92 minutes. Training was not rerun.

Base: `unsloth/Qwen3.5-0.8B`, revision
`23c69c53358a07516b5827588b3fdb12ae78fd65`. Training started from the clean
base, without 4-bit loading, using bf16, rank 16, alpha 32, learning rate
`2e-4`, maximum length 4096, batch size 1, gradient accumulation 16 and seed 0.

There were 493 training examples and 8 internal validation examples. Assistant
responses were retained in full, and loss was calculated only on assistant
tokens. The independent `test.jsonl` was not read.

| Epoch | Optimizer step | Internal validation loss |
| --- | --- | --- |
| 1 | 31 | 0.444826 |
| 2 | 62 | 0.365607 |
| 3 | 93 | 0.358980 |

The lowest internal validation loss was at epoch 3 (`checkpoint-93`). The final
export used epoch 3, matching that checkpoint. Automatic best-checkpoint
selection was not enabled. Mean training loss was 0.351284, and final-step loss
was 0.228121. Losses from different batches are not independent quality
evaluations. Peak PyTorch GPU memory was 2199.7 MiB allocated and 4192 MiB
reserved.

Checkpoints 31/62/93, the final adapter, tokenizer, configuration and SHA256
records were retained. Every existing SHA256 manifest entry was rechecked, and
the adapter tensors were readable.

The following exact GGUF files were selected. The base was exported from the
original pinned snapshot without loading LoRA. Both files use Q4_K_M and exclude
MTP auxiliary layers. Names, shapes and types of all 320 tensors match. CPU
loading and a one-token functional check of the formal fine-tuned GGUF passed
on the local machine.

- `E:\HarborGuard\runs\lora_train\qwen35_08b_20261017_053229_2957\gguf\harborguard-base.Q4_K_M.gguf`
  (529297760 bytes), SHA256
  `9d71d66049417f130e68113b557cab67743a79c55203012c2e75a81602b7bac1`.
- `E:\HarborGuard\runs\lora_train\qwen35_08b_20261017_053229_2957\gguf\harborguard-lora-merged.Q4_K_M.gguf`
  (529297184 bytes), SHA256
  `95704489c1ee021bd52bb0632a7701f76bad70c4e2e5fb9ec84775a712676baa`.

Final adapter:
`E:\HarborGuard\runs\lora_train\qwen35_08b_20261017_053229_2957\adapter`.
See `FINAL_RESULTS.json` for the detailed machine-readable results.

The training and export pipeline completed, with internal validation loss
decreasing across epochs. There were only 8 internal validation examples.
Independent testing and a business-output comparison against the same base
had not yet been performed at the time of this report. These results therefore
do not establish business effectiveness, real-world generalization or an
improvement from fine-tuning. Mac/Ollama deployment and final CPU latency were
not verified in this record.

This review did not update model weights, original data, YOLO checkpoints,
shared source code or the system `metrics.json`.
