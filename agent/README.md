# agent/ —— HarborGuard Agent 服务（负责人 C，端口 8001）

**状态：C3 的 options_ready 云端→本地 Ollama→模板闭环已完成。当前 Z.ai 账户返回
429，因此真实运行降级到 qwen3:1.7b；不得把它记作云端成功。**

```
agent/
  __init__.py
  config.py          # ✅ 已实现：显式 load_dotenv()，全部模型名/地址/超时走配置
  main.py            # FastAPI、/health、/ask、WS 消费与串行任务队列
  context.py         # REST 确定性拉齐上下文，UTF-8 压缩 <= 3 KB
  prompts.py         # 任务书原文系统提示词（云端/本地/后续蒸馏共用）
  router.py          # 云端兼容接口 → Ollama → 模板，总截止时间与统计
  schemas.py         # 六字段严格 pydantic、合法文本截断与全部 ID 校验
  template.py        # 确定性模板建议和事实型问答
  backend_client.py  # REST /api、WS /ws、重连与 since_seq 补事件
```

## 启动

```bash
source .venv/bin/activate
python -m agent.main        # 默认监听 127.0.0.1:8001
```

启动前先运行 B 的后端（默认 `http://localhost:8000`）。Agent 显式读取仓库根目录
`.env`；常用变量是 `BACKEND_BASE_URL`、`BACKEND_WS_URL`、`BACKEND_TIMEOUT_S`、
`AGENT_HOST`、`AGENT_PORT`、`AGENT_EVENT_BUDGET_S`、`AGENT_CLOUD_BUDGET_S`。
`BACKEND_BASE_URL` 必须表示后端根地址，客户端为 REST
统一补 `/api`；`BACKEND_WS_URL` 留空时从根地址推导 `/ws`。

云端现有配置是 Z.ai 的 Anthropic 兼容接口。兼容协议不证明实际服务是 Anthropic
Claude；健康状态与日志分别记录 `provider`、`request_model`、`response_model`。
SDK 隐式重试关闭，凭证不会进入日志。`OLLAMA_MODEL` 当前应为已验证的
`qwen3:1.7b`；`harborguard-lora` 尚未训练或部署。

```bash
curl http://127.0.0.1:8001/health
curl -X POST http://127.0.0.1:8001/ask \
  -H 'Content-Type: application/json' -d '{"question":"当前态势如何？"}'
.venv/bin/python -m pytest -q tests/test_agent_phase1.py tests/test_agent_phase2.py
```

在线链路为：`options_ready` → REST 拉齐真实上下文 → 云端/本地/模板草案 → pydantic
与上下文 ID 双重校验 → `POST /api/recommendations` → 后端广播 `recommendation`。首次连接及重连
都会用 `since_seq` 补事件；相同载荷去重，场景 reset/start 会淘汰排队及处理中旧任务。

事件总预算默认 9.5 秒，预留 0.5 秒给模板和 POST；云端最多占 4 秒。模型返回但
结构/ID 非法时附校验错误重试一次，认证、权限、连接和超时错误直接降级。`state.network`
为 `offline` 时完全跳过云端；`network_up` 会清除云端健康熔断。Ollama 启动时记录冷/热
预热耗时，所有生成 await 都受截止时间取消，模板提交后不会再提交迟到模型结果。

`GET /health` 分开显示模型原始输出、合法输出、重试、错误、超时、已生成路由和已成功
提交路由。当前只处理 `options_ready`；二级警报、灾害和浮标触发留待下一阶段。硬规则
不变：Agent 只解读和推荐，不改警报等级、不调用 `/api/decision`。
