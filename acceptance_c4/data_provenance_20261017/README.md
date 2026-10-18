# C4 数据来源核对

结论：`ml/lora/datasets/test.jsonl` 的 50 条是 `gen_contexts.py` 生成的合成上下文，
不是 `capture_real.py` 截取的真实场景上下文。原指标数值保留，但只能按合成固定
测试集结果解读，不得包装为真实采集性能。

## 可重跑核对

```bash
cd /Users/chrisjiang/Projects/harborguard
.venv/bin/python acceptance_c4/data_provenance_20261017/audit_provenance.py
```

脚本只读文件，不调用云端、Ollama 或后端。它验证固结哈希、逐条来源集合、
`split_records(seed=0)` 的顺序重建、Lenovo 训练输入哈希与 493/8 分割记录。

## 来源链

- 合成原始上下文：`contexts.jsonl` 500 条 + `contexts_extra.jsonl` 80 条。
- 合格合成蒸馏记录：552 条；按 key 排序后用 `seed=0` 洗牌。
- 固定 test50：洗牌后前 50 条，其中 40 条来自首批 500、10 条来自补充 80。
- 合成 train450：随后 450 条。
- 真实场景上下文：`real_contexts.jsonl` 51 条，只追加到训练文件尾部。
- Lenovo 输入：`train.jsonl` 501 条，哈希与 `training_meta.json` 一致；
  前 493 条用于正式训练（450 合成 + 43 实采），末 8 条用于内部验证（均为实采）。
- confirm60：`seed=424242` 的另一合成确认集，与 test50 的精确上下文重复为 0。

`train501` 与 `test50`、`real51` 与 `test50`、`confirm60` 与 `test50` 的精确上下文
重复均为 0。这是基于规范 JSON 上下文的 SHA256 结论；它不等于已证明每条合成
场景在语义上都完全独立。`real_contexts.jsonl` 也没有逐条的 capture-run ID，无法从
该文件单独还原交接说明中三次场景 A/B 采集的批次边界。

## 本轮复算补充

- 三组合成原始上下文均由当前生成器原地只读重建：500/seed0、80/seed1、60/seed424242。
- `confirm60.eval.jsonl` 的 user JSON 带序列化空格，raw contexts 使用紧凑格式；解析后内容
  与顺序 60/60 一致。审计使用规范化 JSON 比较，原始冻结文件没有改写。
- confirm60 与 train501（包含正式 train493 与内部验证8）精确重复均为 0；两组测试各自无内部重复。
- `capture_real` 的“真实”是本机仿真后端实跑上下文，并非真实海域、物理声呐采集。
- 当前文件与固定划分完全吻合；没有发现测试集更换证据。源文件的历史创建时间不能由
  本轮哈希独立证明；FREEZE.md 的生成/评估时间线作为已有记录保留，不伪造新的冻结时间。
- 评估脚本默认读 `ml/lora/datasets/test.jsonl`；confirm60 通过单独 test-path 包装文件评估。
  两次原始日志摘要与 metrics 分别存于 candidate 目录；本轮未重新运行模型或调整配置。
- JSON 模式的整数分子由原始聚合值与已知分母唯一还原，写入正式 metrics 的 `counts`；
  test50 为结构50/50、事实44/50、方案31/33、null14/14，confirm60 为
  结构60/60、事实39/60、方案35/36、null18/18。耗时仍为原评估的3.75/4.71秒。

完整机器可读结果在 [audit.json](audit.json)。哈希与重复结论可复算；它们不能证明所有
相似场景在语义上独立，也不能替代真实海域验证。无需因来源标签错误撤回合成集结果；
任何“真实采集独立测试性能”的声明应撤回。本轮没有触发重新冻结集评估的训练重叠条件。
