# HarborGuard B 后端与算法验收报告

日期：2026-10-17（America/Los_Angeles）。依据原始《HarborGuard 任务书 B · 后端与算法》，面向项目负责人和 A/B/C 队友。

后续声呐安全修复及指定 C `6389b70` 的实际验收见 [候选补充报告](sonar-safety-integration.md)：真实模型 Security 三级为 505s，超过原 500s 上限；浏览器和新版耐久仍待验。下文 37 项统计适用于注明的历史基线，不能直接用于宣布新 C 全部通过；20ms 仍是负责人调整后的尽力目标。

**结论：B 的核心 MVP 已实现并具备有条件的合成演示能力，原始任务书尚未全部验收。** 原始 37 个复选框逐项覆盖：31 PASS、1 FAIL、5 PENDING。FAIL 是原始“每 tick <20ms”的实测结果；负责人已取消其硬性门槛，因此它不再阻塞 Demo，但本报告不把未达阈值改成 PASS。31 个 PASS 中含明确标注版本的历史验收，不表示当前 main 已完整验收。

本轮 B 全量回归 **95 passed / 0 failed / 0 skipped，63.17s**；Ruff、compileall、依赖一致性及样例 TypeScript 严格编译均通过。仅编制 B 报告和隔离验证，没有修改生产代码、A/C 源码、静态坐标、冻结契约或数据库迁移，没有 Push/PR/Merge。

## 依据与证据口径

原始文件为仓库根目录本地提供的 `HarborGuard 任务书 B · 后端与算法.docx`，SHA256：`9291ad36b4c3d38563caa681f4634c107db5723975e28f73d0e2c25cef9fe9ac`。逐条抽取全部 37 个复选框，并自动核对下文要求文字与原文件完全一致；没有从 `docs/acceptance.md` 的完成标记推导结论。原文件未擅自入 Git。

“已实现”指存在源码；“已测试”指有实际执行记录；“PASS”仅适用于记录中的版本和环境；“PENDING”表示指定人员、版本或场地证据不足。不是把“未验证”写成故障。以下 R/H1/H2/H3 用于区分本轮与历史记录：

| 证据 | 精确范围 | 本报告使用方式 |
| --- | --- | --- |
| R 本轮 | B 工作区 `6f862d78bb8458f90237252f4fc6d1629e7b6738`，生产目录与 `04de0fe7abb9eb52ba7ae806beb30131d4b04a8e` 一致 | 新跑95项、数值/几何/契约审计；隔离内存及临时数据库，无浏览器复测 |
| H1 历史原始验收 | 测试组合 `9ed9a4d92c46c0ffa2419ed8145ce4c9de53a26d`；A=`faa7ac16265b4a976c71361d7ee378a6abc27784`，模板C=`78d39574266b01a582b0626c17021181749271c8` | 完整播放、DEBUG地图、三次单机彩排、安装计时；来源分支报告提交 `9049a556bc35cc714b1dcd9091ea5db36aea629d` |
| H2 持久化后稳定B | B=`04de0fe7abb9eb52ba7ae806beb30131d4b04a8e`；实际生产优化提交 `d9a2e89` | 20分钟耐久/性能/重启；另有 A=`98505588c643d55174acf399bb597ca8c9260ec0` 的真实浏览器故障时延 |
| H3 恢复修复复测 | A=`dc69ad28ac37e8d0592d9271f9d61e28c79ff27c`，固定上述B/C；候选 `b48cac76e301a047afa330bced2eae6e388d534c` | 真实浏览器恢复、模板Agent、审批、失败注入、断线、重启、500窗口及PNG |

机器可读证据：[本报告核查记录](evidence/B-final-acceptance-20261017.json)。其中保留了 H1 的原始来源提交、证据哈希、三轮数值及安装步骤。H2/H3 证据链接见报告末尾。

## 当前 Git 与实际交付状态

- 工作分支为 `codex/harborguard-backend-tick-performance`，编制前 HEAD=`6f862d7`，较远程领先1个提交；该提交仅新增 B 回归/文档，尚未 Push。原始 B DOCX 是未跟踪输入文件。
- 官方远程为 `https://github.com/ChrisJiang123/harborguard.git`；本轮 fetch 后 `origin/main=f93af2caa6763ca41c00f05a5a9329939f0dbbe3`，已由仓库维护操作合入 PR #7。A head=`b549515337e0a50889d331ae397e4f381e4694ca`；相对 H3 的三个恢复关键文件仅有英文文案变更，两处已知身份去重逻辑仍在。不能用“已合并”代替“已验收”。
- main 的 `backend/app`、`backend/migrations`、`shared` 与稳定B一致；但 main 仍是 **C0 骨架，没有 `agent/main.py` 等固定模板服务实现**。因此 main 不是已验证的完整 A/B/C 演示包，不能在 main 直接照模板组合的命令声称全套可启动。
- 当前 main 没有重新进行完整浏览器/三轮彩排验收；`origin/demo/mac-integration` 新演示分支也不在本报告已验证范围。没有自动替换为 C 新模型路由。
- 本轮对 `127.0.0.1:5173`、`:8000/api/health`、`:8003/api/health`、`:8001/health` 的4次探测均 ConnectTimeout，**不能确认原演示服务当前在线**。这是当前环境探测结果，不是后端测试失败；未主动停止/重启进程、切换 checkout 或覆盖演示库。恢复演示前需要按所选固定组合启动并检查 health。

## 原始复选框逐项验收

下面每项均给出原始要求、源码/测试位置、实际执行、实测、结果与剩余动作。源码路径相对仓库根目录；测试方法名可直接用于 pytest 定位。历史执行均明确标注，未重新运行的场景不写成本轮通过。


### B0–B1


#### B0–B1-1 PENDING

原始要求：队友 clone 后执行 make backend，GET /api/health 返回 {"ok": true}

- 源码和测试：Makefile:backend；dev.ps1；backend/app/main.py；backend/tests/test_contract.py
- 执行与版本：H1：历史已验证模板组合，非本轮重跑。本轮独立内存 TestClient GET health；历史 H1 全新本地 clone 和三服务启动。未由队友执行 GNU make。
- 实测数据：本轮隔离 health={"ok":true}；历史预装依赖三服务累计 3.063s，新 clone 累计 3.719s。
- 验收结果：**PENDING**。接口正常已有证据；队友本人 clone 后 make backend 的指定验收动作缺少记录，保留 PENDING。


#### B0–B1-2 PASS

原始要求：用一个小 Python 脚本连 /ws：每秒约 5 条 state，seq 连续递增

- 源码和测试：backend/app/api/ws.py；bus.py；main.py；test_api.py::test_websocket_rate_sequence_and_disconnect_cleanup。
- 执行与版本：R：本轮 WS 单测；H2：稳定 B 真实 20 分钟耐久。test_api.py::test_websocket_rate_sequence_and_disconnect_cleanup；引用 H2 真实网络 20 分钟结果。
- 实测数据：H2：1200.08s、6001 条 state、5.000Hz；最新 H3 空闲短样本 4.991Hz。seq 严格递增。
- 验收结果：**PASS**。state/event 共用 seq，state 之间可有跳号；严格递增不等于无间隙连续。5Hz 是实测平均，不是每帧硬实时保证。


#### B0–B1-3 PASS

原始要求：tests/test_contract.py 遍历附录全部 GET 接口，返回体都能被对应 pydantic 模型校验通过

- 源码和测试：backend/app/models.py；api/rest.py；test_contract.py::test_all_contract_get_endpoints。
- 执行与版本：R：本轮 B@6f862d7 复核；生产源码与 B@04de0fe 一致。本轮 95 项 B 全量回归，含 test_contract.py::test_all_contract_get_endpoints 与冻结路径检查。
- 实测数据：21 个 REST 操作＝13 GET＋8 POST；12 JSON GET 按 Pydantic v2 校验，PNG GET 实际解码；14 类事件。
- 验收结果：**PASS**。所有测试通过；PNG 是二进制校验，不把 PNG 当成 JSON Pydantic 模型。


#### B0–B1-4 PENDING

原始要求：样例 JSON 能被 A 的 TypeScript 类型直接使用（A 确认）

- 源码和测试：shared/sample_state.json；sample_events.json；types.ts；frontend/src/types/contract.ts。
- 执行与版本：R：本轮严格 TypeScript 编译；A 的指定确认仍待提供。将 shared 样例直接赋给 StateMsg/EventMsg[]，tsc --noEmit --strict --skipLibCheck --target ES2022。
- 实测数据：tsc exit=0；2 条航迹、1 个三级警报、3 个样例方案、14 类样例事件。
- 验收结果：**PENDING**。技术兼容已验证；没有把编译通过代替原始要求的 A 明确确认。


#### B0–B1-5 PASS

原始要求：A 的前端连上后浏览器控制台无 CORS 报错

- 源码和测试：backend/app/main.py；config.ALLOWED_ORIGINS；test_contract.py::test_cors_and_static_data。
- 执行与版本：R：本轮 CORS 单测；H1/H3：固定 A 的历史浏览器。本轮 CORS preflight 单测；历史 localhost:5173 跨域实际操作和浏览器错误检查。
- 实测数据：localhost:5173 OPTIONS 200 且 allow-origin 正确；历史浏览器未出现 CORS 阻断。H3 候选使用同源代理。
- 验收结果：**PASS**。仅证明已测构型；H3 同源代理不等于允许 5174 跨域，更不等于当前 main 整体验收。


### B2


#### B2-1 PASS

原始要求：tests/test_data.py：shapely 能加载全部多边形且 is_valid；分区 ID 唯一；neighbors 双向对称

- 源码和测试：data/zones.geojson；backend/tests/test_data.py::test_polygons_metadata_and_symmetric_navigation_graph。
- 执行与版本：R：本轮 B@6f862d7 复核；生产源码与 B@04de0fe 一致。本轮 test_data.py 五项数据测试及独立 Shapely/邻接审计。
- 实测数据：12 个唯一且有效多边形；6 berth、4 channel、2 anchorage；非对称邻接 0，几何不接触的邻接对 0。
- 验收结果：**PASS**。示意数据的几何合法性通过；真实海图准确性不由此证明。


#### B2-2 PASS

原始要求：从入口分区出发沿航道 BFS，能到达所有泊位区

- 源码和测试：decision/disaster.py::reopen；test_data.py::test_entrance_reaches_every_berth_through_channels。
- 执行与版本：R：本轮 B@6f862d7 复核；生产源码与 B@04de0fe 一致。本轮从 entrance 只沿 channel 扩展的 BFS 审计；test_data 与 test_disaster。
- 实测数据：全部 6 个泊位区可达；灾害模式仅通行 clear 航道。
- 验收结果：**PASS**。灾害 BFS 只穿过 clear 航道，blocked/unsurveyed 不会越过。


#### B2-3 PENDING

原始要求：10 个浮标都在水域多边形内或紧邻水域（在 geojson.io 上目视确认，不在陆地上）

- 源码和测试：data/buoys.json；test_data.py::test_buoys_are_in_schematic_water_and_assets_in_berths。
- 执行与版本：R：本轮示意几何检查；真实海图验收 PENDING。Shapely 检查浮标在示意水域内；计算每个浮标最近邻米制距离。未执行权威水陆底图目视验收。
- 实测数据：10/10 在示意水域；最近邻约 280.000–492.443m，与建议约 500–800m 有偏差。
- 验收结果：**PENDING**。多边形合法不证明真实不在陆地上。B/A 应对照可靠底图共同核验；未经确认不移动共享坐标。


#### B2-4 PASS

原始要求：A 的地图上能看到真实分区、资产三圈和浮标

- 源码和测试：frontend/src/map2d/*（A 原样）；data/*；test_data.py。
- 执行与版本：H1/H3：固定 A 的真实浏览器及图层检查。真实 2D 浏览器和前端 A2 检查。
- 实测数据：业务图层已加载；12 分区、5 资产三圈、10 浮标；40 船期静态副本一致。
- 验收结果：**PASS**。业务数据确实来自后端，图层可见；此 PASS 仅指实际业务图层显示，不能解释为真实港区海图/测深已验收。


### B3


#### B3-1 PASS

原始要求：geo 往返换算误差 < 0.1 米（测试）

- 源码和测试：backend/app/geo.py；test_simulation.py::test_geo_round_trip_has_sub_decimeter_error。
- 执行与版本：R：本轮 B@6f862d7 复核；生产源码与 B@04de0fe 一致。本轮 4 组坐标往返实测＋test_simulation.py 参数化测试。
- 实测数据：最大误差 4.64408957473e-10m，远小于 0.1m。
- 验收结果：**PASS**。通过。


#### B3-2 PASS

原始要求：UUV 两个航点相距 300 米、速度 1.5 m/s，在 t = 200 ± 1 秒到达（测试）

- 源码和测试：sim/targets.py::UUV；test_simulation.py::test_uuv_reaches_300m_waypoint_at_200_seconds。
- 执行与版本：R：本轮 B@6f862d7 复核；生产源码与 B@04de0fe 一致。1999+1 个 0.1s 步长。
- 实测数据：t199.9s 到299.85m；t200s 到300m、速度归零。
- 验收结果：**PASS**。通过。


#### B3-3 PASS

原始要求：同一种子运行两次，t = 120 秒时所有目标位置完全相同（测试）

- 源码和测试：sim/scenario.py；world.py；test_simulation.py::test_scene_seed_is_repeatable_and_large_steps_match_fixed_steps。
- 执行与版本：R：本轮 B@6f862d7 复核；生产源码与 B@04de0fe 一致。两次固定子步 + 一次120s大步。
- 实测数据：t120s 全部目标位置和速度完全相同；A seed42/B seed7。
- 验收结果：**PASS**。仅用场景派生 numpy Generator，不以墙钟随机化。


#### B3-4 PASS

原始要求：DEBUG_TRUTH_TRACKS=1 跑场景 A，A 的地图上能看到目标按剧本移动

- 源码和测试：engine.py::_truth_tracks；sim/targets.py；test_simulation.py。
- 执行与版本：H1：历史已验证模板组合，非本轮重跑。引用 H1 独立 DEBUG=1 后端与真实 A 浏览器运动检查。
- 实测数据：7 条真值航迹；T1 从 t1 到 t301 坐标改变，地图/目标卡可见；10m 误差圈及显式 DEBUG 标签。
- 验收结果：**PASS**。该条是历史兜底显示测试；算法、耐久和普通 Demo 使用 DEBUG=0。本轮没有重启现有服务跑 DEBUG。


#### B3-5 PASS

原始要求：暂停、继续、1×/4×/10× 倍速、重置都能通过 REST 生效

- 源码和测试：backend/app/api/rest.py；engine.py；backend/tests/test_api.py::test_controls_faults_and_reset
- 执行与版本：R：本轮 B@6f862d7 复核；生产源码与 B@04de0fe 一致。本轮隔离 REST 依次设置 1/4/10，读取 state 核对；全量测试覆盖 pause/resume/reset 和时钟。
- 实测数据：三个请求均 200，返回 speed 分别为 1/4/10；pause 时位置/仿真 t 不变，reset 回 t0/scenario=null。
- 验收结果：**PASS**。主循环10Hz；10× 每外层tick推进1仿真秒，由10个0.1s子步组成。


### B4


#### B4-1 PASS

原始要求：单元测试：3 个浮标观测一个直线目标，30 秒后位置 RMSE < 30 米、速度误差 < 0.3 m/s

- 源码和测试：perception/localize.py；kalman.py；test_perception.py::test_noisy_three_buoy_track_accuracy_velocity_and_id。
- 执行与版本：R：本轮 B@6f862d7 复核；生产源码与 B@04de0fe 一致。本轮按现有三浮标测试独立重算 t30–90 的 61 个样本，并跑完整感知单测。
- 实测数据：位置 RMSE 5.88507m；速度 RMSE 0.171037m/s；单一 ID T1；末椭圆 a=7.21399m/b=3.48527m。
- 验收结果：**PASS**。均低于 30m/0.3m/s；这里是 30 秒后直线窗口，不能混作完整转弯场景速度指标。


#### B4-2 PASS

原始要求：场景 A：UUV 从首次被检测到到抵达泊位，≥ 90% 时间对应同一个航迹 ID（不换号）

- 源码和测试：perception/tracker.py；perception/benchmark.py。
- 执行与版本：H1：完整 A 感知指标；H2：后续优化输出一致性证据。完整A 1200仿真秒真值只用于评分。
- 实测数据：首次检测t1；抵达t1066；T3占965/1066=90.5253%；T60占99。
- 验收结果：**PASS**。抵达前 965/1066=90.5253%，仅窄幅通过；完整 1200s 主 ID 占比 80.4167%。保留换号限制，不换分母美化。


#### B4-3 PASS

原始要求：场景 A 中每 5 分钟仿真时间内，confirmed 的假航迹 ≤ 1 条

- 源码和测试：sim/acoustics.py；perception/localize.py；benchmark.py；test_perception.py。
- 执行与版本：R：纯虚警单测；H1：完整 A 四窗口评分。A全程+300s纯虚警单测。
- 实测数据：A四个300s窗口 confirmed假航迹均0（距最近真值>100m口径）。
- 验收结果：**PASS**。100m评分门限明确披露；纯虚警观测确实产生后仍满足≤1。


#### B4-4 PASS

原始要求：水面船舶航迹 cls 都为 vessel，且不产生警报

- 源码和测试：perception/tracker.py::update；decision/alerts.py；test_perception.py::test_ais_only_uses_nearby_vessels。
- 执行与版本：R：AIS/警报排除单测；H1：3793 个船舶样本评分。全A每秒 confirmed broadband 航迹最近船舶评分 + AIS单测。
- 实测数据：100m评分门内3793个船舶航迹样本全为vessel且L0；违规0。
- 验收结果：**PASS**。AIS生产门限50m未改；不得用AIS覆盖narrowband UUV。


#### B4-5 FAIL

原始要求：10 Hz 下每 tick 处理耗时 < 20 ms

- 源码和测试：backend/app/engine.py::step；perception/classifier.py；backend/tools/benchmark_ticks.py；backend/docs/performance-followup.md
- 执行与版本：H2：优化后独占离线基准/20分钟；另有固定B/C的独立峰值细分诊断。引用真实同步持久化、真实数值链路的完整 A/B 10× 基准和 20 分钟记录。本轮未改变算法或重跑性能。
- 实测数据：A 外层 tick 平均 19.6448ms/P95 27.0585ms/最大 61.0667ms，446/1200 超 20ms；B 最大 113.8246ms；耐久日志最大 120.8ms。
- 验收结果：**FAIL**。按原始严格阈值仍 FAIL；负责人已明确将 20ms 调整为尽力优化目标，所以这项不再阻塞 Demo。保留原始统计，不改写为达标；单子步、外层 tick、PNG、持久化不能混用。


### B5


#### B5-1 PASS

原始要求：风险分项测试：5 个手算用例全部通过

- 源码和测试：decision/risk.py；config.W；test_decision.py::test_risk_five_hand_computed_cases。
- 执行与版本：R：本轮 B@6f862d7 复核；生产源码与 B@04de0fe 一致。5个手算case + 行为/ETA单测。
- 实测数据：C=0.6/0.2/0.05/0.92/0.2；R=0.47/0.35/0.305/0.566/0.35。
- 验收结果：**PASS**。C/P/B/Z/D权重0.30/0.25/0.25/0.15/0.05未改。


#### B5-2 PASS

原始要求：迟滞测试：R 在 0.4 上下来回波动时等级不来回跳

- 源码和测试：decision/alerts.py；test_decision.py::test_alert_hysteresis_and_deleted_track。
- 执行与版本：R：本轮 B@6f862d7 复核；生产源码与 B@04de0fe 一致。0.39/0.41往返及连续低阈值测试。
- 实测数据：t1低、t10恢复、t20再低，t49仍L2，t50才L1；删除发cleared。
- 验收结果：**PASS**。升级立即，降级连续30仿真秒。


#### B5-3 PASS

原始要求：场景 A 以 10× 运行：一级 ≤ 5 秒、二级 15–25 秒、三级 40–50 秒（墙钟时间，通过调场景起点和速度达到）

- 源码和测试：decision/alerts.py；data/scenarios/scenario_a.yaml；test_integration.py。
- 执行与版本：H2：稳定 B 真实 Uvicorn 时序；H1：三次真实彩排；R：场景回归。本轮真实数值场景回归；引用 H2 独立 B HTTP/WS 墙钟测试与 H1 三次模板组合记录。
- 实测数据：稳定 B：L1 3.720s、L2 15.069s、L3 48.339s；H1 三轮 L3 为49.016/48.407/48.406s。
- 验收结果：**PASS**。均在原窗口；墙钟来自实际服务，未用仿真 t/10 代替。不同基线的最早 L1 时刻分别保留。


#### B5-4 PASS

原始要求：二级后发生 ping，detection 事件带 image_url，打开图片能看到框

- 源码和测试：decision/pinger.py；perception/classifier.py；test_decision.py::test_active_sonar_fallback_png_and_all_outbound_event_models。
- 执行与版本：R：classifier/PNG 单测；H3：真实浏览器逐张打开。本轮 C 导入失败/坏输出降级、PNG/事件模型回归；引用 H3 真实浏览器检测图与框检查。
- 实测数据：二级 t150.7 触发 ping；640×640 PNG 可解码；Recovery 四张空 track_id 入口也可打开。
- 验收结果：**PASS**。允许的演示降级已通过；当前 Detection.model="stub"，不构成 YOLO 或真实声呐识别精度验收。


#### B5-5 PASS

原始要求：三级后 1 秒仿真时间内发 options_ready：≥ 2 个局部方案 + 全港关闭；全港关闭的 berths_open_pct = 0 且延误船时最大

- 源码和测试：decision/optimizer.py；test_integration.py::test_security_scene_timing_options_and_manual_approval。
- 执行与版本：R：全场景/优化器回归；H2/H3：真实三级和方案。全A首次三级与options事件比较+优化器单测。
- 实测数据：t483.1 同子步 options_ready，3 局部＋1 全港；全港开放比例0、延误162船时，最小局部6船时。
- 验收结果：**PASS**。仅生成建议；restricted 必须由人工 approve 写入。


#### B5-6 PASS

原始要求：approve 后 state.zones 中对应分区变为 restricted

- 源码和测试：decision/__init__.py::approve；api/rest.py::decision；test_api.py::test_decision_endpoint_requires_valid_human_approval。
- 执行与版本：R：持久化/审批单测；H3：真实 UI 批准/驳回/失败注入。本轮 API、决策、SQLite 失败回滚与重启回归；引用 H3 UI 批准/驳回后刷新和同库重启。
- 实测数据：A11/opt-1 实际 UI approve seq3064，5 个 restricted 分区；reject seq887；写入失败503且没有成功 decision。
- 验收结果：**PASS**。按负责人后续要求，reject 也发布已有 decision 事件并持久化，未增加共享字段；reject 不撤销早先 approve。A 多操作员去重问题另列 I-02。


#### B5-7 PASS

原始要求：哺乳动物禁 ping 规则有单元测试

- 源码和测试：decision/pinger.py::safe；test_decision.py::test_mammal_ping_prohibition_limit_and_duration。
- 执行与版本：R：本轮 B@6f862d7 复核；生产源码与 B@04de0fe 一致。500m保护、cue call、在线浮标、20s/5次/1.5s测试。
- 实测数据：保护区内不ping；超出保护区才允许；计时及次数断言全过。
- 验收结果：**PASS**。未新增硬件发射，所有为仿真。


### B6


#### B6-1 PASS

原始要求：场景 B：墙钟 60 秒内分区陆续变为 clear、unsurveyed、blocked；t = 60 秒浮标失效后至少 1 个分区停在 unsurveyed

- 源码和测试：decision/disaster.py；scenario_b.yaml；test_integration.py::test_disaster_scene_faults_detection_and_connected_reopening。
- 执行与版本：R：完整 B 数值回归；H1：真实 10× 三轮；H3：Recovery 浏览器 smoke。三次真实B10×完整600s仿真。
- 实测数据：H1 首 blocked 0.141/0.156/0.172s，首 clear 1.844/1.828/1.860s；仿真 t60 B4/B7失效；最终6 clear/4 blocked/2 unsurveyed。
- 验收结果：**PASS**。3 种状态在墙钟 60s 内可见；完整600仿真秒耗时约59.938–60.031s。碎片不走安防警报。


#### B6-2 PASS

原始要求：reopen_plan 至少给出 1 条航路和 1 个可复航泊位

- 源码和测试：decision/disaster.py::reopen；test_disaster.py::test_bfs_requires_continuous_clear_channels_and_adjacent_clear_berths。
- 执行与版本：R：BFS 与完整 B 回归；H3：真实浏览器。真实B plan与独立BFS断言。
- 实测数据：route 为 channel_entrance、channel_main_s；可复航 berth_container_1；按 SURVEY_H=1.5h 得 9h。
- 验收结果：**PASS**。9h 为任务书演示公式，不代表真实调查工时或经济收益。


#### B6-3 PASS

原始要求：同一种子跑两次，事件序列（事件名 + t）完全一致

- 源码和测试：backend/tools/record.py；test_integration.py::test_full_replay_deterministic_and_self_contained。
- 执行与版本：R：本轮 B@6f862d7 复核；生产源码与 B@04de0fe 一致。本轮 test_full_replay_deterministic_and_self_contained 对 A/B 各录两次到独立 pytest 临时目录；另含同库 checkpoint 可复现性回归。
- 实测数据：A/B 两次事件名+t 一致，JSONL 字节 SHA256 一致，PNG 实际解码；没有覆盖 frontend/public 的文件。
- 验收结果：**PASS**。不使用外部Agent随机延时作为离线事件时钟。


#### B6-4 PASS

原始要求：每种注入在 A 的界面上 3 秒内可见

- 源码和测试：engine.py::inject；sim/world.py::inject；frontend/src/panels/BuoyGrid.tsx/TopBar.tsx。
- 执行与版本：H2：A@9850558+B@04de0fe+C@78d3957 实际浏览器；非本轮重测。引用 ab-integration-9850558.json 的六类真实浏览器反馈计时。本轮仅跑 B 注入单测。
- 实测数据：buoy_down 383ms、buoy_up 382ms；network_down 383ms、network_up 378ms；noise_up ≤191.521ms、noise_down ≤214.135ms。
- 验收结果：**PASS**。均低于3s，含观察开销；noise 由 REST 触发、前端日志确认。仅模拟业务网络状态；不证明真实 Wi-Fi、LoRa、ESP32 离线。最新 main 未重复本项浏览器计时。


#### B6-5 PASS

原始要求：replay_a.jsonl、replay_b.jsonl 在 A 的回放模式中能完整播放

- 源码和测试：backend/tools/record.py；frontend/src/data/replay*.ts（A原样）；test_integration.py。
- 执行与版本：H1：A@faa7ac1 全程播放；H3：A@dc69ad2 末帧/只读/PNG smoke；R：完整 JSONL 校验。引用 H1 浏览器从0以1×完整播放两文件；H3 仅 seek 末帧与图片；本轮对 A/B 重录两次、校验所有消息及图片。
- 实测数据：历史完整播放 A120000ms/B60000ms；A20:00三级、B10:00复航9h；H3 replay批准禁用、碎片本地PNG640×640。
- 验收结果：**PASS**。PASS 限已有完整播放证据的版本；最新 main 的全程浏览器播放仍 PENDING，不把 seek 写成完整播放。


#### B6-6 PASS

原始要求：向 /api/recommendations POST 非法数据返回 422，合法数据被广播

- 源码和测试：models.py::Recommendation；engine.py::recommend；test_contract.py::test_recommendation_validates_references_and_broadcasts。
- 执行与版本：R：契约/引用/事务单测；H3：真正 C 模板推荐。本轮非法结构/证据/方案ID 422，合法载荷广播及写入失败回滚；引用 H3 C 产生的两条真实建议。
- 实测数据：实际建议 rec-d89ea3415187 与 rec-e3714ebee774；对应警报/方案可查询，延迟恢复期间没有丢失。
- 验收结果：**PASS**。C 仅给建议、不审批。C 模板未实现灾害/浮标建议触发；新 C 路由未验收。


#### B6-7 PASS

原始要求：Agent 未启动时 /api/agent/ask 返回清楚的错误，后端不崩

- 源码和测试：api/rest.py::ask；test_api.py::test_agent_proxy_success_failure_timeout。
- 执行与版本：R：代理成功/502/504回归；H1：真实 Agent 缺席。本轮 MockTransport 回归；历史实际停止自有 C 后调用 B 问答。
- 实测数据：H1 实际2.375s返回清楚502且B health正常；20s超时分支通过MockTransport返回504。
- 验收结果：**PASS**。真实缺席与模拟超时分开说明；本轮不停止他人服务。


### B7


#### B7-1 PASS

原始要求：场景 A、B 各连跑 3 次，关键事件时间偏差 < 3 秒

- 源码和测试：data/scenarios/*；历史 H1 验收观察器与机器可读 rehearsals 记录
- 执行与版本：H1：旧固定 A/B/C 三次单机彩排；非当前 main 三次复验。引用三次实际浏览器参与的单机集成彩排。未冒充 A/C 队友在场，也未声称当前 main 已重跑三遍。
- 实测数据：总耗时260.235/135.594/201.187s；L3极差0.610s，B结束极差0.093s；关键事件误差均<3s。
- 验收结果：**PASS**。历史三轮通过；一次观察器背压超时尝试重跑已披露。三人现场彩排、最新候选三轮验收仍待安排。


#### B7-2 PASS

原始要求：连续运行 20 分钟无报错、内存平稳

- 源码和测试：backend/tools/soak.py；backend/app/main.py；backend/docs/evidence/soak-history.json
- 执行与版本：H2：持久化及性能改进后稳定 B 的真实20分钟；不扩展为最新ABC耐久。引用1200秒真实Uvicorn/HTTP/WS/CPU/RSS和数据库重启验证；本轮未重新运行20分钟。
- 实测数据：1200.08s；6001state/1139event；5.000Hz；最大包26618bytes；CPU平均15.751%/30s窗口最大24.0%；RSS94.89–104.14MB；错误0。
- 验收结果：**PASS**。内存随场景回落，未见持续增长；只覆盖该时长/机器。磁盘历史增长另有保留策略风险，不能把RSS稳定写成数据库不增长。


#### B7-3 PENDING

原始要求：队友按 README 从零启动整套系统 < 5 分钟

- 源码和测试：README.md；backend/README.md；dev.ps1；历史 H1 docs/demo-runbook.md
- 执行与版本：H1：历史已验证模板组合，非本轮重跑。引用本机新clone、独立venv/node_modules、依赖安装/构建及真实三服务启动；队友新电脑从零未执行。
- 实测数据：有缓存本机安装+构建32.922s，再启动3.719s，合计36.641s；预装环境3.063s。
- 验收结果：**PENDING**。不是空缓存/无运行时的新电脑；缺队友本人验收。当前 main 也缺模板 Agent，不得直接把旧用时移植到 main。


#### B7-4 PENDING

原始要求：make test 全绿

- 源码和测试：Makefile:test；dev.ps1:test；pyproject.toml。
- 执行与版本：R：本轮 B 等价 pytest；H3：联合 B+C 回归；GNU make 字面验收未执行。本轮 python -m pytest backend/tests -q（pyproject 默认 testpaths 同为backend/tests）；Ruff、compileall、pip check、样例TS编译。
- 实测数据：95 passed、0 failed、0 skipped，63.17s；上游TestClient弃用警告1条。历史B+C为120passed/2skipped、68.57s。
- 验收结果：**PENDING**。本机无GNU make，严格字面 make test 保留 PENDING；Windows等价测试负载全部通过。历史两项无权重跳过不得计PASS，也不与95简单相加。


## 模块结论汇总

| 模块 | PASS | FAIL | PENDING | 结论与边界 |
| --- | ---: | ---: | ---: | --- |
| B0–B1 | 3 | 0 | 2 | 服务/接口/推送通过；队友 clone/make、A 样例确认待完成 |
| B2 | 3 | 0 | 1 | 示意数据有效且可达；真实水陆/部署核验未完成 |
| B3 | 5 | 0 | 0 | 仿真/固定种子/控制通过，DEBUG地图为历史专项 |
| B4 | 4 | 1 | 0 | 数值质量通过；20ms原阈值未达，已取消硬门槛 |
| B5 | 7 | 0 | 0 | 风险至人工处置主流程通过；不含真实识别精度验收 |
| B6 | 7 | 0 | 0 | 后端与已测历史组合通过；完整播放/注入时延有版本边界 |
| B7 | 2 | 0 | 2 | B耐久、旧组合三次单机通过；队友新环境/GNU make待验收 |
| 合计 | 31 | 1 | 5 | 原始37项未全部验收，不代表当前main全绿 |

5项 PENDING 分别是 B0–B1-1、B0–B1-4、B2-3、B7-3、B7-4。B7-4仅保留GNU make字面执行边界，Python等价测试95项全绿；并非有5项后端功能未实现。真正三人现场彩排、最新整包复验在补充集成要求中单独保留，不通过缩小原复选框统计隐藏它们。

## 持久化和接口一致性补充验收

这部分是负责人后续提出的恢复要求，不假装它们原本就是37个复选框。

| 能力 | 当前结论 | 证据或限制 |
| --- | --- | --- |
| SQLite持久化建议/决策/事件/PNG/运行态 | PASS，B | `storage.py`、`checkpoint.py`、`migrations/001_history.sql`；本轮18条history用例均在95项中 |
| approve/reject结构化事件与原子落库 | PASS，B | 事务提交后才返回成功/广播；真实SQLite失败注入503、没有成功decision；UI重试H3通过 |
| 同库服务重启 | PASS，已测组合 | seq继续增长，场景安全暂停，审批/限制/详情/建议不丢；H3 seq1421→1519 |
| 超过500条内部历史保留 | PASS，B | 数据已归档；本轮526+事件与重启回归；H3归档596事件/3决策时公开窗口仍500 |
| 超过500条公开查询和刷新全恢复 | PENDING，契约限制 | `/api/events`仍只过滤最近500事件；没有分页/总数/截断标志。持久化不等于前端能枚举所有历史 |
| 较早已知ID详情/PNG | PASS，B，范围有限 | 当前对象优先，已知历史ID回退；`/alerts/{id}`不含审批状态，不能冒充审批查询接口 |
| REST恢复期间实时日志/模板建议保留 | PASS，H3 | 旧options延迟3s后仍有新日志；events延迟5s期间真实模板rec到达后保留；原竞态已修复 |
| 真正WS断开/补偿/去重 | PASS，H3已测次序 | 只关闭浏览器WS、B/C继续；三条离线日志有序且各一条；不是network_down代替真断线 |
| 真实seq回退的新会话保护 | PASS，H3 | 人为换新QA库后清旧审批；旧库仍保留记录，不将换库写成普通重启丢历史 |

REST保持21操作、14事件和原字段；Pydantic v2与TypeScript样例已验证。state/event共用seq，所以只能要求严格递增，不要求相邻state差1。当前state没有recommendation/approval字段；审批以结构化decision为准。`/api/log`仅最近1000条、最新在前，reset/start清当前日志；不能解析自由文本反推审批。v1没有审批幂等键/终态定义，合法重复操作可形成不同seq；reject不是撤销approve。

原任务书写“reject只写日志”；后续负责人明确要求在冻结契约已有decision/action=reject允许的范围内补齐结构化发布。B按该既有定义实现，未新增事件类型或状态枚举。需要的全历史分页方案仍只在 [历史交接](history-handoff.md) 中提出，未未经批准实施。

## 尚未关闭的集成问题

### I 01 合法重复日志被前端合并

**FAIL，A负责。** H3在同一暂停时刻连续两次POST相同文本日志，B产生seq143/144两条合法记录；实时页面2条，刷新后1条。`frontend/src/store/useHarbor.ts`的`logIdentity/mergeRecoveredLogs`用`t/level/source/text`的Set把两次业务记录合为一条。

建议A：结构化事件按现有seq去重；REST日志快照没有ID时保留重复记录的多重性。同时测“同一事件重发只一条”和“两次合法同文日志保留两条”。本轮B新增的持久化边界测试已证明两条记录重启后均在，没有修改frontend。

### I 02 实时审批操作员未跟随较新事件

**FAIL，A负责。** H3同t484对A1/opt-1先approve/QA_REMOTE，再approve/QA_REMOTE_2；B持久化并广播后一条seq1520，页面日志已有第二人、卡片仍是第一人，刷新才变第二人。decision的前端key遗漏seq/operator，提前当重复事件忽略。

建议A：在现有generation/session回退保护下按持久化event.seq辨识decision；不同seq不可仅因动作与仿真时刻相同丢弃。增加同刻两个操作员决策及相同seq重发测试；不需要B改共享契约。

### I 03 当前main缺固定模板Agent

**最终整包验收阻塞，需C与负责人处理。** main只有C0骨架，缺少已验证C模板服务与renderer等文件；本报告测试没有把它替换为新云端/Ollama路由。应由负责人确定如何纳入`78d3957`模板基线，再在独立交付分支测试。B不合并main或覆盖C代码。

### I 04 历史窗口和外部验收

公开全历史分页等待契约确认；真实水陆、测深/潮位、真实声呐与权重、现场投影/录屏播放、真实断Wi-Fi与硬件离线、队友从零启动和三人彩排均未在本报告完成。当前stub/template在原B任务书允许的MVP降级范围，不能据此宣称真实识别或硬件效果。

I01/I02阻塞“所有恢复/审批边界完全一致”的宣称；标准单操作员、一次决策、窗口以内的受控演示已在H3通过。20ms和3D chunk约995KB为非阻塞优化项。不要因边界失败否定已测主链路，也不要隐藏边界后宣布整体全绿。

## 性能与稳定性

| 指标 | 实测与范围 | 验收判断 |
| --- | --- | --- |
| 5Hz推送 | H2真实1200.08s，6001 state，5.000Hz；最大状态26618bytes | 该B环境PASS；小于50000bytes |
| CPU | H2单核30秒窗口平均15.751%、最大24.0% | 低于50%；不是瞬时最大值保证 |
| RSS | H2后端及Python子进程94.89–104.14MB，切换后回落 | 20分钟未见持续增长；不是无限时无泄漏证明 |
| 外层tick | A平均19.6448/P95 27.0585/最大61.0667ms；B最大113.8246ms | 原始20ms FAIL；已批准不作硬门槛 |
| 识别与PNG峰值 | 独立峰值诊断A classifier最大46.868ms；B初始4张classifier合计约110.29ms | 主要集中在图像路径，不据此改Kalman/风险算法 |
| 内部子步 | 每个0.1仿真秒；10×外层tick含10子步 | 新版未独立测每个完整子步P95/最大；不能外层除10宣称达标 |
| 持久化磁盘 | H2约111.5MiB，持续保留事件与PNG | 需后续保留策略；不通过删历史压低指标 |

风险最低的下一步是保持当前稳定后端，优先修A恢复和整包启动。固定声呐网格缓存属于C；PNG异步化涉及图片可用时序、原子提交、RNG/回放，不作为比赛前无确认补丁。本轮没有新增性能优化或改统计口径。

## 单机彩排和启动证据

三轮是H1历史固定组合，A/C队友未在现场，不能称为三人验收：

| 轮次 | 总耗时秒 | L1 L2 L3墙钟秒 | 模板建议秒 | Recovery完成秒 | 结果 |
| --- | ---: | --- | ---: | ---: | --- |
| 1 | 260.235 | 0.063 / 15.094 / 49.016 | 49.110 | 60.031 | 真实UI批准、2D/3D、Recovery、回放通过 |
| 2 | 135.594 | 0.110 / 15.125 / 48.407 | 48.453 | 60.031 | 同上；回放seek，完整播放另测 |
| 3 | 201.187 | 0.109 / 15.140 / 48.406 | 48.468 | 59.938 | 同上 |

三轮成功流程无应用层人工重试；另有一次第2轮观察器未持续消费WS导致背压/keepalive超时的未完成尝试，修复观察器后重跑。不能把“三次成功”写成“所有尝试零异常”。H3在持久化后组合补测了两次真实A闭环和Recovery，但没有伪造新版完整三轮记录。

首次安装和启动分开记录：H1有缓存电脑新clone依赖安装/构建32.922s，真实三服务再启动3.719s，总36.641s；预装环境累计3.063s。不是空缓存新电脑或队友本人验收，不能抹掉原始待验收项。当前main缺C模板，本轮四个服务探测超时，所以这些时间不证明当前main可照搬启动。

## 后续复核命令和五分钟演示安排

以下是复核说明，本轮未自动执行重启、安装、录制或合并。先选定包含固定B/C与已测A的独立演示工作区；只有B/C各目录确实为已验证版本时才执行服务命令。不要直接在缺C的main运行Agent。

```powershell
# 在所选演示工作区，已有Python 3.11+和本地虚拟环境
$env:HARBORGUARD_DB = 'C:\HarborGuard\demo\history.sqlite3'
$env:DEBUG_TRUTH_TRACKS = '0'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# 第二终端，固定C模板源码与依赖已准备；本模板无需Ollama/云端密钥
$env:BACKEND_BASE_URL = 'http://127.0.0.1:8000'
$env:BACKEND_WS_URL = 'ws://127.0.0.1:8000/ws'
.\.venv\Scripts\python.exe -m agent.main

# 第三终端，A已安装依赖并完成构建
npm.cmd --prefix frontend run preview -- --host 127.0.0.1 --port 5173
```

数据库父目录须提前创建并可写；同库单worker，保留数据库以恢复历史。启动前检查8000/8001/5173是否被占用，不结束未知进程。前端构建需核对其已有API/WS地址配置；QA8003/8006/5174是历史隔离测试端口，不是冻结生产地址。

```powershell
# 本轮实际成功的后端验证负载；将临时目录换成新的未使用目录
.\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp artifacts/B-acceptance-next
.\.venv\Scripts\python.exe -m ruff check backend/app backend/tools backend/tests
.\.venv\Scripts\python.exe -m compileall -q backend
.\.venv\Scripts\python.exe -m pip check
```

演示前先确认B health返回ok、C health明确model=template、前端LIVE，且本地两份JSONL和PNG存在。五分钟建议按以下顺序：

1. 0:00–0:20：说明合成港区、stub识别、模板建议与人工最终审批；LIVE状态和2D资产/浮标。
2. 0:20–1:20：Security 10×，观察L1→L2→PNG→L3和方案，约49s产生三级；没有及时到达则先核对speed/paused/服务状态，不靠伪造事件补齐。
3. 1:20–2:10：对比局部与全港方案，展示真实模板建议；单操作员批准一次，核对restricted；暂停后刷新验证窗口内恢复。
4. 2:10–2:40：切3D和回2D；强调水面/DEM为演示参考，不宣称真实测深。
5. 2:40–3:50：Recovery 10×，展示碎片PNG、B4/B7故障、clear/blocked/unsurveyed和BFS复航/9h假设值。
6. 3:50–4:40：切Replay展示离线数据和只读保护，可明确说明跳到关键帧；不是现场重新验收完整播放。服务有故障优先保留错误记录再切回放，不清演示库掩盖问题。
7. 4:40–5:00：说明已验证能力与剩余边界，结束录制。

## 任务书目标覆盖

| 原始目标 | 已验证能力 | 仍有的限制 |
| --- | --- | --- |
| 洛杉矶港水下安防数字孪生 | 示意分区与资产、声学观测、定位、Kalman航迹、三级风险和PNG证据链 | 不是真实港区测绘或真实声呐性能验收；抵达后航迹仍有换号 |
| 量化局部响应并由人处置 | 局部方案与全港基线、开放泊位/延误/残余风险、批准后限制、驳回留痕 | 指标是任务书演示公式；前端两项去重边界未关闭 |
| 灾后分区复航 | 勘测覆盖、碎片阻塞、浮标故障、clear航道BFS和可复航泊位 | 非真实灾害调查，不把9小时假设写成实际节省 |
| 可复现和离线兜底 | 固定种子、消息及PNG一致性、两份JSONL、只读回放 | 500事件外公开历史仍受冻结契约限制；未证明硬件或真实断网能力 |
| 团队集成与比赛交付 | 固定模板组合主链路、历史三次单机彩排、本轮95项后端回归 | 当前main缺模板C，现场三人/新电脑/最终录屏验收未完成 |

这些能力符合B任务书的MVP方向，不能代替完整赛题规则及整队交付验收。任务书明确允许C的渲染/模型未就绪时由B标注stub降级，因此“允许的B降级流程通过”和“真实AI识别效果通过”是两个不同结论。

## 交付判断与分工

**B任务书未全部通过；稳定B具备可测试、可对接的MVP。** 受控录制可以基于固定A/B/C组合准备，但当前main缺模板C、两项A一致性边界仍失败且本轮服务在线状态未确认，不能无条件称“当前main可现场演示/可最终提交”。Devpost素材可准备，正式赛题评分细则、最终整包、跨设备录屏和团队签字仍需检查，不宣称已经提交或通过主办方验收。

- A：仅在frontend修复I01/I02，保留已通过的generation/延迟保护；以新SHA复验同文重复日志、同刻双操作员和真实刷新/重连；完成投影电脑与录屏可读性。
- B：保持当前稳定实现和本轮95项回归；等待A修复后在独立库组合复测；联合核验港区几何，待负责人确认才做历史分页或共享坐标变更。本报告不请求对已授权普通工作重复审批。
- C：与负责人安排固定78d3957模板进入最终整包，核对renderer/依赖/health；新模型路由单独验收，真实权重未就绪继续明示stub，Agent不代替人工审批。
- 负责人：确认历史分页最小提案、指定最终整合提交并安排三人现场及队友启动验收。当前PR#7已由仓库合并，本报告不执行任何main合并或远程修改。

## 可审查证据

- [本报告逐项数据与本轮审计](evidence/B-final-acceptance-20261017.json)
- [稳定B性能与新版耐久](performance-followup.md)，[20分钟原始摘要](evidence/soak-history.json)
- [峰值诊断及负责人最新20ms口径](demo-stability-followup.md)，[分项诊断](evidence/peak-analysis-20261017.json)
- [真实进程持久化验证](history-verification.md)，[实际恢复/审批fixture与契约边界](history-handoff.md)
- [A9850558真实浏览器联调](ab-integration-9850558.md)，[六类注入/联调JSON](evidence/ab-integration-9850558.json)
- [Adc69ad2修复复测及A修复建议](pr7-recovery-dc69ad2.md)，[实际seq/时间/结果证据](evidence/pr7-recovery-dc69ad2.json)

H1较早报告仅在本地`codex/harborguard-b-final-acceptance@9049a556bc35cc714b1dcd9091ea5db36aea629d`，可用`git show <SHA>:docs/B-final-acceptance.md`与`docs/B-acceptance-evidence.json`复核。其“reject仅日志”“无持久化”“20ms硬门槛”“旧A竞态”属于当时状态；以本报告和H2/H3明确更新为准，不混用旧结论。

本轮完整JUnit、几何/数值审计、原文抽取和样例TS编译输入保留于忽略目录`artifacts/B-acceptance-20261017/`；Git中仅新增本报告与小型JSON证据，没有数据库、缓存、日志、密钥或原始任务书附件。
