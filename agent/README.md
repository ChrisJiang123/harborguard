# agent/ —— HarborGuard Agent 服务（负责人 C，端口 8001）

**状态：C3 模板建议在线闭环已完成；云端、Ollama 与 LoRA 路由暂未接入。**

```
agent/
  __init__.py
  config.py          # ✅ 已实现：显式 load_dotenv()，全部模型名/地址/超时走配置
  main.py            # FastAPI、/health、/ask、WS 消费与串行任务队列
  context.py         # REST 确定性拉齐上下文，UTF-8 压缩 <= 3 KB
  schemas.py         # 严格 pydantic 模型、字段截断与真实 ID 校验
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
`AGENT_HOST`、`AGENT_PORT`。`BACKEND_BASE_URL` 必须表示后端根地址，客户端为 REST
统一补 `/api`；`BACKEND_WS_URL` 留空时从根地址推导 `/ws`。

```bash
curl http://127.0.0.1:8001/health
curl -X POST http://127.0.0.1:8001/ask \
  -H 'Content-Type: application/json' -d '{"question":"当前态势如何？"}'
.venv/bin/python -m pytest -q tests/test_agent_phase1.py
```

在线链路为：`options_ready` → REST 拉齐真实上下文 → 模板草案 → pydantic 与上下文
ID 双重校验 → `POST /api/recommendations` → 后端广播 `recommendation`。首次连接及重连
都会用 `since_seq` 补事件；相同载荷去重，场景 reset/start 会淘汰排队及处理中旧任务。

当前只实现本轮要求的 `options_ready` 安防模板链路，`model` 恒为 `template`。云端、
Ollama、LoRA、二级警报、灾害和浮标触发留待后续。硬规则不变：Agent 只解读和推荐，
不改警报等级、不调用 `/api/decision`。
