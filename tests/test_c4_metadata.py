"""C4 metadata publication must preserve historical failures across repeated runs."""
import json
import runpy
from pathlib import Path


def test_republishing_metrics_preserves_schema_failure_and_integer_counts(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    relative = Path('acceptance_c4/candidate_json_20261017')
    candidate = tmp_path / relative
    candidate.mkdir(parents=True)
    archive = candidate / 'archived_metrics/metrics.schema-mode-failure.20261017.json'
    archive.parent.mkdir()
    original = repo / relative / 'archived_metrics/metrics.schema-mode-failure.20261017.json'
    archive.write_bytes(original.read_bytes())
    for name in ('metrics_candidate_json.json', 'metrics_confirm60.json'):
        (candidate / name).write_bytes((repo / relative / name).read_bytes())
    writer = candidate / 'write_official_metrics.py'
    writer.write_bytes((repo / relative / writer.name).read_bytes())
    (candidate / 'confirm60.eval.jsonl').write_bytes(b'isolated confirmation fixture\n')
    official = tmp_path / 'ml/lora/metrics.json'
    official.parent.mkdir(parents=True)
    official.write_bytes((repo / 'ml/lora/metrics.json').read_bytes())
    for name in ('harborguard.gguf', 'harborguard-base.gguf', 'datasets/train.jsonl', 'datasets/test.jsonl'):
        path = official.parent / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b'isolated metadata fixture\n')
    for _ in range(2):
        runpy.run_path(str(writer))
        assert archive.read_bytes() == original.read_bytes()
        result = json.loads(official.read_text())
        assert result['history_schema_mode']['full_metrics'] == json.loads(original.read_text())
        assert result['lora']['counts']['id_fact_valid'] == {'pass': 44, 'total': 50}
        assert result['confirm60_synthetic']['lora']['counts']['id_fact_valid'] == {'pass': 39, 'total': 60}
        assert result['lora']['counts']['option_agree'] == {'pass': 31, 'total': 33}
