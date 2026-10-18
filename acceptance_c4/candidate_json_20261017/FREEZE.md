# 候选配置冻结（2026-10-17）
- 冻结内容：OLLAMA_FORMAT_OVERRIDES 机制（frozen_config.diff）+ 候选值
  `harborguard-lora:json,harborguard-base:json`（qwen3:1.7b 不在表中=继续完整 schema）
- 冻结依据：dev9（训练样本 9 条）经真实 eval 路径确认实现（frozen_dev9_confirm.json）：
  LoRA 结构合法 100%/100%、ID+事实 89%/89%、方案一致 100%(n=3)、null 100%(n=6)、2.09s/条
- 单元验证：test_format_overrides.py 6/6 PASS（默认空=全 schema 现状不变；显式生效；非法抛错）
- 冻结后：三方 50 条冻结 test 评估，不按其结果改提示词/参数/checkpoint
- 回退方式：清空 OLLAMA_FORMAT_OVERRIDES（代码默认路径与 C3 完全一致）

## 补充冻结（2026-10-17 15:36 生成 / 15:48 记录）
- 确认集 confirm60：`confirm_contexts_seed424242_n60.jsonl`（gen_contexts --n 60 --seed 424242，含故障注入）
  包装版 `confirm60.eval.jsonl` sha256 = d6360787f9bda3d828bd2cdb0ac3990da63cf4793b210a28867f71f239e9aa28
- 时间线：确认集生成于候选 50 条评估完成之前（15:36 < 15:47），未用于任何诊断或调参
- 来源修正：50 条 test 也是 `gen_contexts.py` 合成上下文，可由 552 条合格合成蒸馏
  记录按 `split_records(seed=0)` 逐条同序重建；不是 capture_real 实采。confirm60 为
  `seed=424242` 另一合成确认集，与 test50 精确重复为 0。两组结果均保留独立
  整数分母，不代表真实场景泛化。详见 `acceptance_c4/data_provenance_20261017/`。
- Lenovo 键序材料复测（字节保真确认）：Mac/Ollama 上 success/failure 两种顺序在 dev2 全部循环，
  仅 format=json 通过——键序杠杆在 Mac 运行时不可达，候选维持 format=json。
