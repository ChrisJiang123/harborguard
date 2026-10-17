"""ml/yolo/infer.py（SonarDetector）测试（C2）。

- 权重缺失必须抛 FileNotFoundError（契约：B 捕获后改用桩，不伪造预测）。
- 用 .cache/yolo26n.pt（COCO 预训练，仅验证推理链路，非声呐权重）冒烟：
  灰度图输入、强制 CPU、返回结构与 bbox 有效性。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.yolo.infer import SonarDetector  # noqa: E402

SMOKE_WEIGHTS = ROOT / ".cache/yolo26n.pt"  # check_c0 下载的 COCO 预训练权重（gitignored）


def test_missing_weights_raise_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="权重不存在"):
        SonarDetector(weights=str(tmp_path / "nope.pt"))


@pytest.mark.skipif(not SMOKE_WEIGHTS.is_file(), reason="无 .cache/yolo26n.pt（先跑 check_c0 下载）")
def test_detect_contract_with_pretrained_smoke():
    from ml.sonar.render import render_ping

    det = SonarDetector(weights=str(SMOKE_WEIGHTS), conf=0.25)
    img, _ = render_ping(
        [dict(cls="debris", range_m=120.0, bearing_deg=0.0, length_m=10.0,
              width_m=4.0, aspect_deg=0.0)],
        max_range_m=150.0, seed=3, size=640,
    )
    out = det.detect(img)  # 灰度 2D 输入
    assert isinstance(out, list)
    for d in out:  # 若有检出，逐项校验契约结构
        assert set(d) == {"cls", "conf", "bbox"}
        assert isinstance(d["cls"], str) and d["cls"]
        assert 0.0 <= d["conf"] <= 1.0
        x1, y1, x2, y2 = d["bbox"]
        assert all(isinstance(v, int) for v in (x1, y1, x2, y2))
        assert 0 <= x1 < x2 <= 640 and 0 <= y1 < y2 <= 640


@pytest.mark.skipif(not SMOKE_WEIGHTS.is_file(), reason="无 .cache/yolo26n.pt")
def test_detect_rejects_bad_input():
    det = SonarDetector(weights=str(SMOKE_WEIGHTS), conf=0.25)
    import numpy as np

    with pytest.raises(ValueError):
        det.detect(np.zeros((4, 4, 4, 4), dtype=np.uint8))
