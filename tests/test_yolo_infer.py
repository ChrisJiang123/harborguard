"""C2 SonarDetector contract tests.

- Missing weights must raise FileNotFoundError for B's explicit stub fallback.
- Optional cached COCO weights exercise grayscale input, forced CPU and valid
  output/bboxes only; they do not establish sonar detection quality.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.yolo.infer import SonarDetector  # noqa: E402

SMOKE_WEIGHTS = ROOT / ".cache/yolo26n.pt"  # Ignored COCO weights cached by check_c0.


def test_missing_weights_raise_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="weights do not exist"):
        SonarDetector(weights=str(tmp_path / "nope.pt"))


@pytest.mark.skipif(not SMOKE_WEIGHTS.is_file(), reason="Missing optional cached COCO smoke weights .cache/yolo26n.pt")
def test_detect_contract_with_pretrained_smoke():
    from ml.sonar.render import render_ping

    det = SonarDetector(weights=str(SMOKE_WEIGHTS), conf=0.25)
    img, _ = render_ping(
        [dict(cls="debris", range_m=120.0, bearing_deg=0.0, length_m=10.0,
              width_m=4.0, aspect_deg=0.0)],
        max_range_m=150.0, seed=3, size=640,
    )
    out = det.detect(img)  # Two-dimensional grayscale input.
    assert isinstance(out, list)
    for d in out:  # Validate every returned detection against the contract.
        assert set(d) == {"cls", "conf", "bbox"}
        assert isinstance(d["cls"], str) and d["cls"]
        assert 0.0 <= d["conf"] <= 1.0
        x1, y1, x2, y2 = d["bbox"]
        assert all(isinstance(v, int) for v in (x1, y1, x2, y2))
        assert 0 <= x1 < x2 <= 640 and 0 <= y1 < y2 <= 640


@pytest.mark.skipif(not SMOKE_WEIGHTS.is_file(), reason="Missing optional cached COCO smoke weights .cache/yolo26n.pt")
def test_detect_rejects_bad_input():
    det = SonarDetector(weights=str(SMOKE_WEIGHTS), conf=0.25)
    import numpy as np

    with pytest.raises(ValueError):
        det.detect(np.zeros((4, 4, 4, 4), dtype=np.uint8))
