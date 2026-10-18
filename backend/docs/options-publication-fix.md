# B：方案指标更新广播修复（待审阅，未推送）

测试源码：`e1b33055883b6bef8e003fc61a2c9f43178cfac1`，分支`codex/harborguard-options-publication`，基于官方main `a841bf9a70d8bf8237b9e03763852a34bed10368`。原修复提交`fe0681e7be706ba33a39dfc8dd1e8b2589749de1`；e1仅把最新main合入自己的独立分支，没有Merge main或改队友远程分支。

## 问题与改动

最终验收真实浏览器在Security t914发现REST方案残余风险55%，最近options_ready及Agent/页面仍50%。优化器正常重算，`DecisionEngine`只按封区/限速几何去重；几何不变时风险、船时、泊位比例、受影响船数及排序变化未广播。问题归属B，不能要求A轮询掩盖。

只修改：

- `backend/app/decision/__init__.py`：去重签名包含当前契约的完整Option字段和ranked。方案变化才发布，相同载荷仍不重复发布。
- `backend/tests/test_option_publication.py`：5项参数化回归覆盖风险、船时、泊位比例、船数及排序独立变化，验证旧事件不被修改、广播载荷合法、检查点往返仍去重、建议不自动封区。

不改优化算法、风险参数、30仿真秒重算周期、审批机制、冻结接口或事件种类。相对a841的生产差异仅6行增加/2行删除，另有48行测试。没有frontend/agent/ml/shared/data变更。

## 实际测试

| 检查 | 结果及范围 |
| --- | --- |
| 新5项回归用于官方main | 5 FAIL（RED），证明既有缺陷；不是将232项已有测试说成失败 |
| e1全量`pytest backend/tests tests agent/tests -q` | **237 PASS、0 FAIL、2 SKIP，152.24秒**；两项缺另一份COCO冒烟权重，交付YOLO实际执行 |
| Ruff/compileall、最新前端build | PASS；不改A/C源码 |
| 真实B+C+WS | e1新库，DEBUG_TRUTH_TRACKS=0、单worker；t632 REST=最新options_ready，risk=0.10，实际C template摘要0.10 |
| 实际浏览器 | 同一A a841页面表格10%、Agent0.10；截图与JSON保留。GUI Reject成功；第二操作员API Reject也持久化，均不产生restricted |
| 运行指标 | 251个state，4.988394Hz，最大间隔349.020ms，最大25585B，RSS峰值430.74MiB，CPU单核等效48.76% |
| 检查点与写入 | 5项新增回归验证签名检查点往返；既有持久化/写入失败/同库重启回归包含在237项内。e1没有再做完整真实进程重启浏览器测试 |

首次基于5a68的fe修复另跑216 PASS/2 SKIP、真实A1200/B600各3次重复和完整浏览器Security→Approve→Recovery→Replay。真实B语义哈希与修复前相同；A多了应发布的方案事件，哈希变化符合预期。**不能将旧fe浏览器全流程自动计到最新e1**；e1全量237项包含真实B专项，当前e1真实浏览器专项只验上述方案一致及Reject。

## 风险与尚未解决项

- 30仿真秒计算周期不变，指标变化时事件数量会合理增加；没有为20ms关闭检测或减少算法正确性。
- 旧检查点签名在下一次优化可能多发一次完整方案；通用tuple序列化可读，之后正常去重；不绕过指纹。
- A R2仍失败：e1 t632两次reject seq1158/1201，Operator A后为QA_CURRENT_2，B两条均落库且无restricted，前端仍显示旧Operator A。其余A历史恢复边界也未由此补丁修复。
- 500事件窗口、仿真真值依赖、3D环境不可用、合成模型误差保持原有范围；不声称真实复航或全系统验收通过。
- C cloud/local/LoRA运行时本轮SKIP；实际建议为template。

独立预览`http://127.0.0.1:5182/`（B8018/C8019），数据库`artifacts/latest-candidate/final-main.sqlite3`；旧正式演示和库未动。原始日志/JUnit/JSON/截图在`artifacts/latest-candidate/`，小型证据见[JSON](evidence/options-publication-20261017.json)。

**未Push、未创建/更新PR、未Force Push、未Merge main。** 交付范围与结果已可审阅；待负责人明确允许后再推送此独立分支，不能把本地修复当作main已包含。
