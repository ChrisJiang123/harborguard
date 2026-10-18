# HarborGuard LoRA 正式训练结果

完成时间：2026-10-17T05:44:24.395707-07:00。3轮、93个优化器步骤，训练约9.55分钟，含加载与导出总计约11.92分钟。没有重跑训练。

基座：unsloth/Qwen3.5-0.8B，revision 23c69c53358a07516b5827588b3fdb12ae78fd65。从干净基座开始，非4-bit、bf16；rank16、alpha32、lr2e-4、max_len4096、batch1、梯度累积16、seed0。

493条训练、8条内部验证；assistant完整保留且仅assistant计损失。独立test.jsonl没有读取。

| 轮次 | 优化器步 | 内部验证loss |
|---|---|---|
| 1 | 31 | 0.444826 |
| 2 | 62 | 0.365607 |
| 3 | 93 | 0.358980 |

最低内部验证loss在第3轮（checkpoint-93）。最终导出使用第3轮，与最低loss检查点一致；训练没有启用自动best检查点选择。
平均训练loss 0.351284，最后一步loss 0.228121。不同批次loss不是独立质量评估。
PyTorch显存峰值 allocated 2199.7 MiB，reserved 4192 MiB。

checkpoint-31/62/93、最终适配器、tokenizer、配置及SHA256均保留；全部已有SHA256清单条目通过复核，适配器张量可读取。

精确选择以下GGUF文件；基座从原始固定快照导出，未加载LoRA。两端均Q4_K_M并排除MTP辅助层，320个张量的名称/形状/类型一致。正式微调GGUF本机CPU加载及1-token功能检查通过。

- `E:\HarborGuard\runs\lora_train\qwen35_08b_20261017_053229_2957\gguf\harborguard-base.Q4_K_M.gguf`（529297760字节）
  SHA256：`9d71d66049417f130e68113b557cab67743a79c55203012c2e75a81602b7bac1`
- `E:\HarborGuard\runs\lora_train\qwen35_08b_20261017_053229_2957\gguf\harborguard-lora-merged.Q4_K_M.gguf`（529297184字节）
  SHA256：`95704489c1ee021bd52bb0632a7701f76bad70c4e2e5fb9ec84775a712676baa`

最终适配器：`E:\HarborGuard\runs\lora_train\qwen35_08b_20261017_053229_2957\adapter`。详细机器可读结果见FINAL_RESULTS.json。

当前结论：训练及导出链路完成，内部验证loss逐轮下降。只有8条内部验证，尚未进行独立测试或同基座的业务输出对照，不能据此声称业务效果、真实场景泛化或微调提升已得到证明。Mac/Ollama部署及最终CPU耗时未验证。

本次复核没有更新模型权重、原始数据、YOLO检查点、共享源码或系统metrics.json。
