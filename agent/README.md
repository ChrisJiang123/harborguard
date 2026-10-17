# agent/ —— HarborGuard Agent 服务（负责人 C，端口 8001）

**状态：C3 的四类事件、确定性事实检查和 OpenRouter→本地 Ollama→模板闭环已完成。
本机云端显式选择 OpenRouter；旧 Anthropic/Z.ai 适配保留但不会被旧凭据自动启用。**

```
agent/
  __init__.py
  config.py          # ✅ 已实现：显式 load_dotenv()，全部模型名/地址/超时走配置
  main.py            # FastAPI、/health、/ask、WS 消费与串行任务队列
  context.py         # REST 确定性拉齐上下文，UTF-8 压缩 <= 3 KB
  factcheck.py       # 可复算事实、方案规则、证据不足条件与评估边界
  prompts.py         # 任务书原文系统提示词（云端/本地/后续蒸馏共用）
  router.py          # OpenRouter/旧云端适配 → Ollama → 模板，总截止时间与统计
  schemas.py         # 六字段严格 pydantic、合法文本截断与全部 ID 校验
  template.py        # security/disaster/buoy 确定性模板和事实型问答
  backend_client.py  # REST /api、WS /ws、重连与 since_seq 补事件
```

## 启动

```bash
source .venv/bin/activate
python -m agent.main        # 默认监听 127.0.0.1:8001
```

启动前先运行 B 的后端（默认 `http://localhost:8000`）。Agent 显式读取仓库根目录
`.env`；常用变量是 `BACKEND_BASE_URL`、`BACKEND_WS_URL`、`BACKEND_TIMEOUT_S`、
`AGENT_HOST`、`AGENT_PORT`、`AGENT_EVENT_BUDGET_S`、`AGENT_CLOUD_BUDGET_S`、
`AGENT_FAILURE_LOG`。云端必须显式设置 `CLOUD_PROVIDER`；未设置时为 `disabled`，不会
因为进程里存在 `ANTHROPIC_AUTH_TOKEN` 等旧变量而意外启用旧服务。
`BACKEND_BASE_URL` 必须表示后端根地址，客户端为 REST
统一补 `/api`；`BACKEND_WS_URL` 留空时从根地址推导 `/ws`。

当前 OpenRouter 配置为 `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`，固定模型
`google/gemini-2.5-flash`。推荐生成使用 `RecommendationDraft.model_json_schema()`、
`response_format.type=json_schema`、`strict=true` 和 `provider.require_parameters=true`；
不支持这些参数的端点必须返回错误，不能静默取消结构约束。SDK `max_retries=0`，同时设置
`provider.allow_fallbacks=false`，由 Agent 的整体截止时间统一控制降级。请求携带
`usage.include=true`；`/health` 仅展示已发生请求的 token、OpenRouter 回传费用、上游 provider
及实际响应模型，不会为健康检查发送收费请求。密钥只从 `.env`/进程环境读取且不进入日志。

旧 `CLOUD_PROVIDER=anthropic` 适配仍可显式启用；协议兼容不证明实际服务是 Anthropic Claude。
本轮不再访问 Z.ai。`OLLAMA_MODEL` 当前应为已验证的 `qwen3:1.7b`；
`harborguard-lora` 尚未训练或部署。

```bash
curl http://127.0.0.1:8001/health
curl -X POST http://127.0.0.1:8001/ask \
  -H 'Content-Type: application/json' -d '{"question":"当前态势如何？"}'
.venv/bin/python -m pytest -q tests/test_agent_phase1.py tests/test_agent_phase2.py tests/test_agent_phase3.py
```

在线链路为：事件 → REST 拉齐真实上下文 → 云端/本地/模板草案 → pydantic、上下文 ID、
确定性事实三道校验 → `POST /api/recommendations` → 后端广播 `recommendation`。触发包括
`options_ready`、升到二级的 `alert_changed`、`reopen_plan` 和变为 down 的 `buoy_changed`。
首次连接及重连都会用 `since_seq` 补事件；相同载荷去重，`reopen_plan` 同计划不重复且
最多每 20 秒仿真时间一次，场景 reset/start 会清理载荷去重、节流和过期任务。

事件总预算默认 9.5 秒，预留 0.5 秒给模板和 POST；云端最多占 4 秒。模型返回但
结构、ID 或明确事实矛盾时附校验错误重试一次，认证、权限、连接和超时错误直接降级。`state.network`
为 `offline` 时完全跳过云端；`network_up` 会清除云端健康熔断。Ollama 启动时记录冷/热
预热耗时，所有生成 await 都受截止时间取消，模板提交后不会再提交迟到模型结果。

事实检查覆盖浮标离线数量及 ID、覆盖数量、识别置信度、方案风险/延误、任务书方案规则、
空方案和 disaster/buoy 的 null 推荐，以及证据不足条件。否定句会先分类，`没有浮标离线`
不会因包含“离线”被误拒。不能可靠复算的自由文本不会冒充已验证，`/health` 明示检查范围。
事实失败样例只保存校验所需事实与哈希化 ID 到 `agent/runtime/`，该目录不入 Git，也不自动
进入蒸馏数据。

`GET /health` 分开显示首次结构合格、首次事实合格、全部原始输出、重试、模型成功、模板兜底、
token 与接口回传费用。2026-10-17 的 OpenRouter 实测：结构化探测 2199.8 ms；真实后端
security/options_ready 2635.0 ms、buoy/down 5435.8 ms、disaster/reopen_plan 1874.2 ms，
三者均提交 `model=cloud`。隔离的 20 次真实生成与 POST 为 20/20 首次结构合格、20/20 首次
事实合格、cloud/local/template=20/0/0、0 次重试；生成到 POST 的中位 1416.1 ms、P95
2086.0 ms、最大 2264.2 ms，接口回传 23,498 tokens 和 $0.0129571。该费用只代表当次接口
返回值，不据价格表反推。

断网实测 cloud 调用数为 0，本地 4707.6 ms；恢复后 cloud 2298.2 ms。隔离无效云端凭据和
不可达 Ollama 在 49.1 ms 内返回 `model=template`，未修改真实凭据。`/api/agent/ask` 实测
673.6 ms、`model=cloud`。硬规则不变：Agent 只解读和推荐，不改警报等级、不调用
`/api/decision`。确定性规则仍不能验证任意自由文本语义，边界由 `/health.fact_check_scope` 明示。
