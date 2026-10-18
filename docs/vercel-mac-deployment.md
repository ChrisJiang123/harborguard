# Vercel 前端与 Mac 后端隧道部署准备

2026-10-17（America/Los_Angeles）。本轮已完成部署分支、生产构建、地址检查和本地浏览器烟测；尚未创建 Vercel 部署或公开隧道，不代表最终集成/安全验收通过。

## 版本与分支

部署分支：`codex/vercel-mac-tunnel-20261017`。代码提交：`e4d3f14e288acf5379edd86b6decc0d27db15d85`；其后的交付文档提交不改变应用代码，最终部署 SHA 见交付消息或 `git rev-parse origin/codex/vercel-mac-tunnel-20261017`。

先 fetch、核对远端分支包含关系后，选择 `e9ae07fbf1e233d83c983803b3992b165eae163c` 为基线：检查时所有其他远端分支的 tip 都已是它的祖先，而非根据 main 名称推断。`origin/demo/mac-integration=a02eb04` 与该 main 的文件树相同；`origin/fix/3d-shoreline-realism=94e9a4c` 也已包含。

收尾再次 fetch 后，main 新增 `d2d4c6fbdff72de5b2d2c02aab0c39723513f3a8`（#20，分支 `codex/harborguard-submission-latest=51d69b3`），仅变更 README、中文 README 和两份投稿文案。已核对 `frontend/`、`backend/`、`agent/`、`ml/` 与所选 e9ae07f 基线完全相同；部署分支保留刚验证的功能版本，不额外合入投稿文案，也不合并到 main。

| 内容 | 已包含提交 |
| --- | --- |
| 最新岸线/3D、英文历史记录显示 | `00462e7`、`6d52b14`，集成 tip `94e9a4c` |
| B 方案/指标更新广播 | `fe0681e`（#16 已合并） |
| B 未决保护、匿名观测与投影修复 | `6353421`、`97a8c75` |
| C4 配置切换、测试集来源修正 | `6da0831`、`7c96ae1` |
| C 实际模型自检、默认英文与模板、几何 helper | `e091506` |
| C 冻结时延、真实权重三轮及实际回退证据 | `9a14731` |
| 本轮前端部署配置 | `df6df167831ff589378dd4492f8b165a8332fa2c` |
| 本轮后端跨域配置 | `e4d3f14e288acf5379edd86b6decc0d27db15d85` |

原项目工作区仍在 `6b18abb` 且有其他终端未提交内容；本轮复用独立受管理工作区 `/Users/chrisjiang/.codex/worktrees/c-acceptance-fixes/harborguard`，未切换、暂存或覆盖原工作区文件。现有 5173/8000/8001 进程不能仅凭端口或 health=200 被认定运行了此部署提交。

## Vercel 参数

| 设置 | 值 |
| --- | --- |
| Repository | `ChrisJiang123/harborguard` |
| Git branch | `codex/vercel-mac-tunnel-20261017` |
| Root Directory | `frontend` |
| Framework Preset | Vite |
| Node.js | `24.x`（本地验证 `24.19.0`） |
| Install Command | `npm ci`，保留现有 package-lock.json |
| Build Command | `npm run build` |
| Output Directory | `dist`（相对 frontend，即仓库 frontend/dist） |

先从指定分支创建 Preview；创建部署时核对分支与 SHA，避免导入仓库时默认选择 main。若以后指定为 Production，按 Vercel 的 Environments → Production → Branch Tracking 设置该分支，无需合并 main。[官方分支说明](https://vercel.com/docs/git#production-branch)。

在所用的 Preview/Production 环境分别设置：

```dotenv
VITE_API_BASE=https://<Mac隧道域名>/api
VITE_WS_URL=wss://<同一个Mac隧道域名>/ws
VITE_BATHYMETRY_URL=/data/seabed-dem.json
```

`VITE_*` 是公开的构建时配置。API base 需要 `/api`，WS 需要 `/ws`；不加入密钥、用户名密码或 token。修改隧道地址后必须重新构建部署。Vercel 构建时会校验 HTTPS/WSS、拒绝缺失值和回环地址；本机日常构建保留原 localhost 默认行为。本轮生产包已确认不会退回 localhost:8000。

REST、指标、问答与声呐图由 `src/data/api.ts` 的 `VITE_API_BASE` 生成；地图资源 API 由 `store/useMapData.ts` 读取同一变量；WebSocket 使用 `data/ws.ts` 的 `VITE_WS_URL`。声呐图根据 detection ID 生成配置域名下的 URL，不把后端相对 image_url 错当成 Vercel 静态文件。问答请求层已有 `/api/agent/ask`，当前页面没有独立问答输入框，本轮没有增加该功能。

`frontend/vercel.json` 按 [Vercel Vite SPA 官方说明](https://vercel.com/docs/frameworks/frontend/vite#using-vite-to-make-spas) 添加回退到 `/index.html` 的 rewrite。它只负责前端页面刷新；API 与 WS 直接到隧道，不借 SPA rewrite 代理 API/WS。前端普通构建无需 Python，也不触发地图下载/重建、模型训练或推理。

## Mac 服务和隧道

浏览器从 Vercel 获取静态文件；REST 和 WebSocket 均经同一个 HTTPS/WSS 隧道到 Mac 的 8000。Agent 8001 和 Ollama 11434 保持本机服务，不需要额外公开端口。

本机尚未安装可用的 `cloudflared` 或 Vercel CLI；Vercel 可使用网页导入。本轮未安装工具、启动隧道或改动共享服务。后续切换 8000/8001 必须先与占用端口的联调终端约好窗口，并在所选部署分支中启动 B 和 C；不要发布仍在旧 6b18abb 工作区运行的服务来冒充此版本。

以下命令仅供切换窗口执行，工作目录必须是所选提交的干净工作区；继续使用现有 Python 环境与本机密钥文件，不创建环境、训练模型或删除原数据库：

```sh
# B 终端：填入实际 Vercel 页面 origin（不要带 /api 或页面路径）。
# 首次演示用独立数据库；保留旧验收数据库和原服务日志。
ALLOWED_ORIGINS='https://<实际前端域名>,http://localhost:5173,http://127.0.0.1:5173' \
DEBUG_TRUTH_TRACKS=0 HARBORGUARD_DB=backend/runtime/vercel-demo-20261017.sqlite3 \
/Users/chrisjiang/Projects/harborguard/.venv/bin/python -m uvicorn backend.app.main:app \
  --host 127.0.0.1 --port 8000 --workers 1

# C 终端：免费连通烟测禁用云端；本机 .env 中的密钥不进入前端。
# --env-file 使用既有文件；显式进程变量优先于文件。
CLOUD_PROVIDER=disabled BACKEND_BASE_URL=http://127.0.0.1:8000 \
BACKEND_WS_URL=ws://127.0.0.1:8000/ws AGENT_LANG=en \
OLLAMA_MODEL=harborguard-lora OLLAMA_FORMAT_OVERRIDES=harborguard-lora:json \
/Users/chrisjiang/Projects/harborguard/.venv/bin/python -m uvicorn agent.main:app \
  --env-file /Users/chrisjiang/Projects/harborguard/.env \
  --host 127.0.0.1 --port 8001 --workers 1

# 独立隧道终端：cloudflared 已安装后执行。
cloudflared tunnel --url http://127.0.0.1:8000
```

跨域变量由后端进程在创建应用时读取；仅编辑 .env 不会改变已运行的服务。未配置变量时继续允许原两个本机来源；显式配置时按完整列表替换。只允许实际前端 origin，不使用所有 vercel.app 的通配来源。本轮没有改动 config.py/检查点指纹、物理参数、审批规则或 P0 算法。

Quick Tunnel 的随机域名每次重建会变化；演示时保持该终端运行。需要固定域名时使用命名 Tunnel。Cloudflare 官方确认 [Tunnel 支持 WebSocket](https://developers.cloudflare.com/cloudflare-one/faq/cloudflare-tunnels-faq/#does-cloudflare-tunnel-support-websockets)；[Quick Tunnel](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) 只适用于开发/测试，存在 200 个在途请求限制且无可用性保证，不应被表述为已完成正式生产运维。

得到隧道域名后，先验证 `/api/health`，再把该 HTTPS/WSS 域名写入 Vercel 环境变量并部署。填入真实前端 origin 后，需要让本分支的后端配置生效；新增/更换 Preview URL 也要更新允许来源。核对 Agent `/health` 的模型、格式与语言；首次免费烟测的路由为本地 LoRA → template，恢复既有 OpenRouter 路由须另按演示安排协调 C 服务配置。

## 本轮验证与保留事项

- 生产构建通过，Node 24.19.0 / Vite 8.3.4；8 个缺失、HTTP/WS、回环、URL 凭证/查询参数反例均在构建阶段被拒绝。构建包中 localhost:8000 后端地址为 0；保留现有锁定依赖，未升级库。
- `npm run lint`、`check:deployment`、`check:a3`、`check:recovery` 通过。问答请求层验证公开域名、POST 内容和既有 19 秒预算，没有模型请求。完整 Python 回归 **260 passed in 50.77s**，云端关闭；4 个新增 CORS 用例覆盖默认来源、指定 Vercel 来源、本机来源及拒绝未列出来源。
- 生产包本地 5187 预览：`/`、首页刷新、`/operations` 直接打开及刷新共 4 项通过；4 次 WebSocket 均使用配置的 WSS URL。页面实际恢复推荐，指标卡显示 harborguard-lora、test50/confirm60、44/50 与 39/60 及事实限制；声呐图加载成功。页面错误 0，访问本机 8000/8001 的请求 0，收费云端调用 0。
- 浏览器使用受控 HTTPS/WSS 契约测试数据，不是真实公网隧道或模型验收。真实 Vercel 路由、跨设备公网 HTTP/WS、实际 CORS 和部署后刷新均 **PENDING**。3D bundle 仍有 >500kB 构建警告，未以传输烟测代替 3D 性能验收。
- B：既有碎片危险区不 clear 的特定复验已记录，不等于所有 P0 关闭。0m 近场仍未观测、保持 unsurveyed；真实接收端漏检、匿名几何观测的仿真假设、AIS 真值耦合及复杂多目标关联边界继续保留。场景 A 三级警报 **505.0s ×3** 超过 400–500s 目标；不调参或修改后端算法掩盖失败。
- C4：英文隔离 local/template=0/10，中文 LoRA 输出不能计为英文成功；test50/confirm60 在 ≤10s 内分别 **44/50、21/60**，事实分别 **44/50、39/60**。两组均为合成数据；报告历史失败和整数分母不变。
- 既有 A 恢复/多操作员/竞态问题继续按原报告跟踪；本轮正向刷新和既有脚本通过不豁免先前失败。真实 Wi-Fi、投影可读性、跨设备试播与完整现场验收仍待负责人确认。

可查 [构建与浏览器证据](evidence/vercel-mac-preparation-20261017.json)、[生产页面截图（受控测试数据）](evidence/vercel-mac-preparation-20261017.png)，以及原 [C 复验附注](C-acceptance-20261017-1743-retest-20261017-1911.md) 和 [B P0 审计](../backend/docs/survey-p0-audit.md)。本轮只按前端、后端、文档分别提交并普通 push 到部署分支，不合并 main、不强推。
