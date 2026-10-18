# Development File Inventory

2026-10-17 follow-up: missing #3/#6 handoff materials were migrated against main `782d04d`; see [integration scope](final-integration-report.md). Added backend/tools/integration_bundle.py, four corresponding tests, B fixtures/integration/, docs/frontend-integration.md, docs/integration/openapi.json, final report/JSON, and the five-minute runbook. Original #6 JSON is preserved in docs/archive. A/C production source and the frozen contract were not changed by that handoff.

The 95-file inventory below is the initial MVP's historical list, not the current repository or this translation's change count.

The initial MVP added or modified 95 files covering B implementation, shared contract, demo data, replay, and verification. Upstream C source stayed unchanged; B entries were appended to root README and .gitignore. The original taskbook was not modified.

## Startup and Dependencies — 7 Files

- [.gitattributes](../.gitattributes)
- [.gitignore](../.gitignore)
- [Makefile](../Makefile)
- [README.md](../README.md)
- [dev.ps1](../dev.ps1)
- [pyproject.toml](../pyproject.toml)
- [requirements-lock.txt](../requirements-lock.txt)

## Backend Code and Tests — 45 Files

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

## Static Data and Scenarios — 8 Files

- [data/README.md](../data/README.md)
- [data/assets.json](../data/assets.json)
- [data/build_demo_data.py](../data/build_demo_data.py)
- [data/buoys.json](../data/buoys.json)
- [data/scenarios/scenario_a.yaml](../data/scenarios/scenario_a.yaml)
- [data/scenarios/scenario_b.yaml](../data/scenarios/scenario_b.yaml)
- [data/vessels.json](../data/vessels.json)
- [data/zones.geojson](../data/zones.geojson)

## Shared Contract and Samples — 4 Files

- [shared/contract.md](../shared/contract.md)
- [shared/sample_events.json](../shared/sample_events.json)
- [shared/sample_state.json](../shared/sample_state.json)
- [shared/types.ts](../shared/types.ts)

## Frontend Static Data and Replay — 24 Files

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

## Documentation and Verification — 7 Files

- [docs/acceptance.md](../docs/acceptance.md)
- [docs/files.md](../docs/files.md)
- [docs/internal_interfaces.md](../docs/internal_interfaces.md)
- [docs/perception_metrics_a_1200.json](../docs/perception_metrics_a_1200.json)
- [docs/perception_metrics_a_600.json](../docs/perception_metrics_a_600.json)
- [docs/soak_metrics.json](../docs/soak_metrics.json)
- [docs/validation.md](../docs/validation.md)
