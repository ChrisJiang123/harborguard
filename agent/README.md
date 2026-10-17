# agent/ —— HarborGuard Agent 服务（负责人 C，端口 8001）

**状态：C0 已建骨架 + `config.py`；C3 起实现其余模块。**

```
agent/
  __init__.py
  config.py          # ✅ 已实现：显式 load_dotenv()，全部模型名/地址/超时走配置
  main.py            # C3：FastAPI，GET /health、POST /ask，WS 客户端 + 串行任务队列
  context.py         # C3：REST 拉齐上下文，压缩 <= 3 KB
  prompts.py         # C3：系统提示词（云端/本地/蒸馏三处共用）
  schemas.py         # C3：pydantic RecommendationDraft + ID 存在性校验
  router.py          # C3：云端(15s) -> 本地 Ollama(30s) -> 模板
  template.py        # C3：无模型兜底建议
  backend_client.py  # C3：WS 重连 + since_seq 补事件 + REST 封装
  tests/
```

## 启动（C3 完成后）

```bash
source .venv/bin/activate
python -m agent.main        # 读取 .env 中 AGENT_HOST / AGENT_PORT
```

完整启动顺序、环境变量表、常见故障处理在 C5 定稿本 README。
硬规则：Agent 只解读和推荐，不改警报等级、不调用 `/api/decision`。
