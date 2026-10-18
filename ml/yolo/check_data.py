"""C2 pretraining dataset check using actual Ultralytics loaders: check_det_dataset resolves paths,
build_yolo_dataset reads every image/label. Seed0 full data expects3400train/600val. Run python
ml/yolo/check_data.py from the repository root.
"""


from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def count(data_yaml: str = str(ROOT / "ml/yolo/sonar.yaml")) -> int:
    from ultralytics.cfg import get_cfg
    from ultralytics.data import build_yolo_dataset
    from ultralytics.data.utils import check_det_dataset

    cfg = get_cfg(overrides={"task": "detect", "mode": "train", "data": data_yaml, "imgsz": 640})
    data = check_det_dataset(data_yaml)  # Same parsing chain used for training.
    print(f"[check] YAML parsed OK: train={data['train']}  val={data['val']}")
    print(f"[check] Classes: {data['names']}")

    ok = True
    for split, expect in (("train", 3400), ("val", 600)):
        ds = build_yolo_dataset(cfg, img_path=data[split], batch=16, data=data, mode=split)
        n = len(ds.im_files)
        empty = sum(1 for lb in ds.labels if len(lb.get("segments", [])) == 0 and len(lb.get("bboxes", [])) == 0)
        print(f"[check] {split}: loaded {n} images (expected {expect}), including {empty} negatives (empty labels)")
        if n != expect:
            ok = False
    print(f"[check] Result: {'PASS' if ok else 'Count mismatch; check dataset generation first'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(count())
