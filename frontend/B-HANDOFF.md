# 给 B 的后端缺口复现（契约冻结期）

记录日期：2026-10-17。本文只描述 A 前端在当前冻结契约下无法补齐的状态；A 未修改后端、数据库或共享契约。

> 2026-10-18 复核：以下“当前”均是历史记录，不代表今天运行态。现有 `backend/app/decision/__init__.py` 已对 approve/reject 都生成结构化 decision，`storage.py`/`engine.py` 已有持久化与检查点恢复，不能继续说“拒绝只写日志”或“后端完全未持久化”。但冻结的 `/api/events` 仍读取 500 条缓存，没有分页历史列表；持久化存在不等于前端能查询全部旧审批。本轮 `127.0.0.1:8000/api/health` 连接被拒绝，未实测当前后端重启/审批往返，也未运行或修改 B 测试。最新 B 验收报告已在远端 main `8613834` 的 `backend/docs/B-final-acceptance.md`，其历史证据不是 A 本轮重跑结果。前端复核结论以 `ACCEPTANCE-A.md` 为准。

## 1. `/api/events` 只能覆盖最近 500 条

涉及接口：`GET /api/events?since_seq={seq}`、`GET /api/log?limit={n}`。

当前实测：

```text
GET /api/health                  -> {"ok":true}
GET /api/events?since_seq=0      -> HTTP 200，当前返回 151 条
首条：{"type":"event","seq":1563,"t":0.0,"event":"scenario_changed",...}
GET /api/log?limit=3             -> HTTP 200，返回 3 条
```

当前实现的 `EVENT_CACHE_SIZE` 为 500，`/api/events` 返回内存事件队列中符合 `since_seq` 的部分，没有分页游标、总数或“已截断”标志。复现历史覆盖不足：持续运行或注入事件直到总数超过 500，刷新前端，再请求 `GET /api/events?since_seq=0`；最早事件已不在响应中。`/api/log` 是自由文本记录，不能作为审批状态的权威来源。

预期行为：由 B 在后端和契约流程中提供持久化、可分页的建议/审批历史，或者至少提供明确的截断标志和稳定游标。记录需要稳定 ID、关联建议/方案 ID、当前状态、时间和结构化决策信息。后端重启后应仍可查询。

前端影响：当前 A 只能在响应恰好达到 500 条时提示“历史不完整”，不能恢复更早的建议、批准或驳回；也无法区分“刚好总计 500 条”和“已被截断”。实时事件仍正常衔接，前端使用已有 recommendation/detection/alert ID 及事件字段去重。

## 2. 历史缺口：驳回没有结构化 `decision` 事件（源码已修复，运行态待复验）

涉及接口：`POST /api/decision`、`GET /api/events`、WebSocket `/ws`。

请求示例：

```json
{
  "alert_id": "A1",
  "option_id": "opt-1",
  "action": "reject",
  "operator": "操作员 A"
}
```

当前路由成功响应为 `{"ok":true}`。当前决策实现只在 `action == "approve"` 时追加 `decision` 事件；`reject` 仅追加一条 `source: "operator"` 的自由文本 `log` 事件。仓库中的后端 API 测试也只断言驳回 HTTP 成功和区域未受限，没有断言驳回事件。此次本机运行态尝试复现时，场景 A 在当前港区数据下到 `t=90` 只有一级警报、没有可提交方案，因此没有伪造一条成功的运行态响应；以上结论来自当前实际路由响应定义和执行分支检查。

复现步骤：准备一个有三级警报且 `options_ready` 的场景；记录当前最大 `seq`；提交上述驳回；查询 `GET /api/events?since_seq={seq}` 或监听 `/ws`。实际只有 `log`，没有 `event: "decision"`。刷新后前端无法权威判断该警报是已驳回还是仍未处理。

预期行为：驳回写入成功后，发布与批准同结构的 `decision` 事件，至少包含 `alert_id`、`option_id`、`action: "reject"`、`operator` 和事件时间；如支持原因，应使用契约化字段。持久化失败时 `/api/decision` 不应返回成功。

前端影响：当前 A 在驳回 HTTP 成功后显示“状态无法确认”并锁定重复提交；若以后收到结构化 `decision`，会自动替换为已确认状态。刷新后未收到结构化事件的记录也不会被错误显示成“待审批”，且前端不会解析日志文本猜测结果。

## B 完成后的联调验收点

1. 批准和驳回后刷新，均从结构化历史恢复相同状态。
2. 产生超过 500 条事件后，早期记录仍可分页读取，并明确返回是否还有前页。
3. 后端重启后记录仍存在。
4. 查询历史后再接 WebSocket，按稳定 ID 去重，无重复、无状态回退。
5. A 只在 B 完成契约评审后接入新字段或新接口；冻结期不自行扩展共享类型。
