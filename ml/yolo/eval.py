"""C2 YOLO sonar evaluation. Evaluate validation mAP50/mAP50-95/class recall and mean CPU latency
over20 sequential images, then write the taskbook metrics.json schema. --device0 permits GPU
validation but CPU timing remains CPU. Missing weights fail without placeholder data. Run python
ml/yolo/eval.py.
"""


from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # Permit direct invocation with the runtime Python.
    sys.path.insert(0, str(ROOT))
DEFAULT_WEIGHTS = ROOT / "ml/yolo/weights/best.pt"
DEFAULT_DATA = ROOT / "ml/yolo/sonar.yaml"
METRICS_PATH = ROOT / "ml/yolo/metrics.json"
CLASS_NAMES = ("uuv", "fish_school", "debris", "marine_mammal")
N_LATENCY = 20


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Evaluate YOLO sonar detection and write ml/yolo/metrics.json")
    p.add_argument("--weights", default=str(DEFAULT_WEIGHTS))
    p.add_argument("--data", default=str(DEFAULT_DATA))
    p.add_argument("--device", default="cpu", help="Validation device (cpu/0/...); latency measurement always uses CPU")
    p.add_argument("--n-latency", type=int, default=N_LATENCY)
    args = p.parse_args(argv)

    weights = Path(args.weights)
    if not weights.is_file():
        print(f"[eval] Missing weights: {weights}; metrics.json was not written (train first; see ml/yolo/train.md)")
        return 1
    if not Path(args.data).is_file():
        print(f"[eval] Missing dataset config: {args.data}; run gen_dataset first")
        return 1

    from ultralytics import YOLO

    model = YOLO(str(weights))
    print(f"[eval] Evaluating {args.data} validation set (device={args.device})...")
    m = model.val(data=str(args.data), split="val", device=args.device, verbose=False)

    # Per-class recall:DetMetrics.class_result(i)->(p,r,ap50,ap).
    names = dict(model.names or {})
    recall: dict[str, float] = {}
    for i in range(len(names)):
        r = m.box.class_result(i)[1]
        name = names.get(i, str(i))
        recall[str(name)] = round(float(r), 4)

    # Mean CPU latency overN validation images after one warmup.
    from ml.yolo.infer import SonarDetector

    detector = SonarDetector(weights=str(weights), conf=0.25)
    import cv2

    from ultralytics.data.utils import check_det_dataset

    data = check_det_dataset(str(args.data))
    val_img_dir = Path(data["val"])
    im_files = sorted(val_img_dir.glob("*.png")) + sorted(val_img_dir.glob("*.jpg"))
    if not im_files:
        print(f"[eval] No validation images: {val_img_dir}")
        return 1
    sample = (im_files * (args.n_latency // len(im_files) + 1))[: max(args.n_latency, 1)]
    imgs = [cv2.imread(str(f), cv2.IMREAD_GRAYSCALE) for f in sample]
    detector.detect(imgs[0])  # Warmup.
    t0 = time.perf_counter()
    for im in imgs:
        detector.detect(im)
    cpu_ms = (time.perf_counter() - t0) * 1000.0 / len(imgs)

    metrics = {
        "model": "yolo26n",
        "data": "synthetic",
        "n_val": len(im_files),
        "mAP50": round(float(m.box.map50), 4),
        "mAP50_95": round(float(m.box.map), 4),
        "recall": recall,
        "cpu_ms_per_image": round(cpu_ms, 1),
    }
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"[eval] Wrote {METRICS_PATH}")
    ok = metrics["mAP50"] >= 0.8 and metrics["cpu_ms_per_image"] < 100
    print(f"[eval] Acceptance threshold (mAP50>=0.8 and CPU<100ms): {'PASS' if ok else 'FAIL; check annotation boxes first'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
