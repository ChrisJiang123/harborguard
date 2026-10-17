# 本次开发文件清单

## 后续前后端联调交付

后端主体已由仓库方通过 PR #2 合入 main。本轮在相同 feature 分支补充以下 8 个文件；不修改生产 API、模型、共享契约、C 代码或 A 前端源码。

- [backend/README.md](../backend/README.md)：联调入口和 Git 状态说明。
- [backend/tools/integration_bundle.py](../backend/tools/integration_bundle.py)：从真实路由导出现有 Schema 与静态样例。
- [backend/tests/test_integration_bundle.py](../backend/tests/test_integration_bundle.py)：21 个 REST 覆盖、Mock 契约、图片及导出一致性。
- [docs/frontend-integration.md](frontend-integration.md)：完整联调交接。
- [docs/integration/openapi.json](integration/openapi.json)：现有 OpenAPI 导出。
- [frontend/public/mock/backend.json](../frontend/public/mock/backend.json)：A 可直接 fetch 的 REST/state/event Mock。
- [docs/files.md](files.md)：本文件。
- [docs/validation.md](validation.md)：本轮测试、烟测与提交检查结果。

以下为原 PR #2 的 95 个文件清单，供追溯。

本次新增或修改 95 个文件，覆盖 B 端实现、共享契约、演示数据、回放与验证记录。上游 C 源码保持原样；根 README 与 .gitignore 追加 B 的内容。原始任务书未修改。

## 启动与依赖 共 7 个

- [.gitattributes](../.gitattributes)
- [.gitignore](../.gitignore)
- [Makefile](../Makefile)
- [README.md](../README.md)
- [dev.ps1](../dev.ps1)
- [pyproject.toml](../pyproject.toml)
- [requirements-lock.txt](../requirements-lock.txt)

## 后端代码与测试 共 45 个

- [backend/README.md](../backend/README.md)
- [backend/__init__.py](../backend/__init__.py)
- [backend/app/__init__.py](../backend/app/__init__.py)
- [backend/app/api/__init__.py](../backend/app/api/__init__.py)
- [backend/app/api/rest.py](../backend/app/api/rest.py)
- [backend/app/api/ws.py](../backend/app/api/ws.py)
- [backend/app/bus.py](../backend/app/bus.py)
- [backend/app/config.py](../backend/app/config.py)
- [backend/app/decision/__init__.py](../backend/app/decision/__init__.py)
- [backend/app/decision/alerts.py](../backend/app/decision/alerts.py)
- [backend/app/decision/disaster.py](../backend/app/decision/disaster.py)
- [backend/app/decision/optimizer.py](../backend/app/decision/optimizer.py)
- [backend/app/decision/pinger.py](../backend/app/decision/pinger.py)
- [backend/app/decision/risk.py](../backend/app/decision/risk.py)
- [backend/app/decision/zones.py](../backend/app/decision/zones.py)
- [backend/app/engine.py](../backend/app/engine.py)
- [backend/app/geo.py](../backend/app/geo.py)
- [backend/app/main.py](../backend/app/main.py)
- [backend/app/models.py](../backend/app/models.py)
- [backend/app/perception/__init__.py](../backend/app/perception/__init__.py)
- [backend/app/perception/benchmark.py](../backend/app/perception/benchmark.py)
- [backend/app/perception/classifier.py](../backend/app/perception/classifier.py)
- [backend/app/perception/kalman.py](../backend/app/perception/kalman.py)
- [backend/app/perception/localize.py](../backend/app/perception/localize.py)
- [backend/app/perception/tracker.py](../backend/app/perception/tracker.py)
- [backend/app/sim/__init__.py](../backend/app/sim/__init__.py)
- [backend/app/sim/acoustics.py](../backend/app/sim/acoustics.py)
- [backend/app/sim/scenario.py](../backend/app/sim/scenario.py)
- [backend/app/sim/targets.py](../backend/app/sim/targets.py)
- [backend/app/sim/world.py](../backend/app/sim/world.py)
- [backend/tests/conftest.py](../backend/tests/conftest.py)
- [backend/tests/test_api.py](../backend/tests/test_api.py)
- [backend/tests/test_bus.py](../backend/tests/test_bus.py)
- [backend/tests/test_classifier.py](../backend/tests/test_classifier.py)
- [backend/tests/test_contract.py](../backend/tests/test_contract.py)
- [backend/tests/test_data.py](../backend/tests/test_data.py)
- [backend/tests/test_decision.py](../backend/tests/test_decision.py)
- [backend/tests/test_disaster.py](../backend/tests/test_disaster.py)
- [backend/tests/test_integration.py](../backend/tests/test_integration.py)
- [backend/tests/test_perception.py](../backend/tests/test_perception.py)
- [backend/tests/test_simulation.py](../backend/tests/test_simulation.py)
- [backend/tools/__init__.py](../backend/tools/__init__.py)
- [backend/tools/make_samples.py](../backend/tools/make_samples.py)
- [backend/tools/record.py](../backend/tools/record.py)
- [backend/tools/soak.py](../backend/tools/soak.py)

## 静态数据与场景 共 8 个

- [data/README.md](../data/README.md)
- [data/assets.json](../data/assets.json)
- [data/build_demo_data.py](../data/build_demo_data.py)
- [data/buoys.json](../data/buoys.json)
- [data/scenarios/scenario_a.yaml](../data/scenarios/scenario_a.yaml)
- [data/scenarios/scenario_b.yaml](../data/scenarios/scenario_b.yaml)
- [data/vessels.json](../data/vessels.json)
- [data/zones.geojson](../data/zones.geojson)

## 共享契约与样例 共 4 个

- [shared/contract.md](../shared/contract.md)
- [shared/sample_events.json](../shared/sample_events.json)
- [shared/sample_state.json](../shared/sample_state.json)
- [shared/types.ts](../shared/types.ts)

## 前端使用的静态数据与回放 共 24 个

- [frontend/public/data/assets.json](../frontend/public/data/assets.json)
- [frontend/public/data/buoys.json](../frontend/public/data/buoys.json)
- [frontend/public/data/vessels.json](../frontend/public/data/vessels.json)
- [frontend/public/data/zones.geojson](../frontend/public/data/zones.geojson)
- [frontend/public/replay_a.jsonl](../frontend/public/replay_a.jsonl)
- [frontend/public/replay_assets/a/det-1.png](../frontend/public/replay_assets/a/det-1.png)
- [frontend/public/replay_assets/a/det-10.png](../frontend/public/replay_assets/a/det-10.png)
- [frontend/public/replay_assets/a/det-11.png](../frontend/public/replay_assets/a/det-11.png)
- [frontend/public/replay_assets/a/det-12.png](../frontend/public/replay_assets/a/det-12.png)
- [frontend/public/replay_assets/a/det-13.png](../frontend/public/replay_assets/a/det-13.png)
- [frontend/public/replay_assets/a/det-14.png](../frontend/public/replay_assets/a/det-14.png)
- [frontend/public/replay_assets/a/det-2.png](../frontend/public/replay_assets/a/det-2.png)
- [frontend/public/replay_assets/a/det-3.png](../frontend/public/replay_assets/a/det-3.png)
- [frontend/public/replay_assets/a/det-4.png](../frontend/public/replay_assets/a/det-4.png)
- [frontend/public/replay_assets/a/det-5.png](../frontend/public/replay_assets/a/det-5.png)
- [frontend/public/replay_assets/a/det-6.png](../frontend/public/replay_assets/a/det-6.png)
- [frontend/public/replay_assets/a/det-7.png](../frontend/public/replay_assets/a/det-7.png)
- [frontend/public/replay_assets/a/det-8.png](../frontend/public/replay_assets/a/det-8.png)
- [frontend/public/replay_assets/a/det-9.png](../frontend/public/replay_assets/a/det-9.png)
- [frontend/public/replay_assets/b/det-1.png](../frontend/public/replay_assets/b/det-1.png)
- [frontend/public/replay_assets/b/det-2.png](../frontend/public/replay_assets/b/det-2.png)
- [frontend/public/replay_assets/b/det-3.png](../frontend/public/replay_assets/b/det-3.png)
- [frontend/public/replay_assets/b/det-4.png](../frontend/public/replay_assets/b/det-4.png)
- [frontend/public/replay_b.jsonl](../frontend/public/replay_b.jsonl)

## 说明与验证 共 7 个

- [docs/acceptance.md](../docs/acceptance.md)
- [docs/files.md](../docs/files.md)
- [docs/internal_interfaces.md](../docs/internal_interfaces.md)
- [docs/perception_metrics_a_1200.json](../docs/perception_metrics_a_1200.json)
- [docs/perception_metrics_a_600.json](../docs/perception_metrics_a_600.json)
- [docs/soak_metrics.json](../docs/soak_metrics.json)
- [docs/validation.md](../docs/validation.md)
