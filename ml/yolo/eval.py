"""ml/yolo/eval.py —— YOLO 声呐检测评估（C2）。

用法::

    .venv/bin/python ml/yolo/eval.py                       # CPU 评估 + 写 metrics.json
    .venv/bin/python ml/yolo/eval.py --device 0            # 训练机上 GPU 评估，CPU 耗时仍单测
    .venv/bin/python ml/yolo/eval.py --weights path/best.pt

在 val 集上算 mAP50 / mAP50-95 / 各类召回，CPU 连续推理 20 张取平均耗时，
写入 ml/yolo/metrics.json（任务书 C2 给定 schema）。
权重缺失时报错退出，不写任何占位数据。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEIGHTS = ROOT / "ml/yolo/weights/best.pt"
DEFAULT_DATA = ROOT / "ml/yolo/sonar.yaml"
METRICS_PATH = ROOT / "ml/yolo/metrics.json"
CLASS_NAMES = ("uuv", "fish_school", "debris", "marine_mammal")
N_LATENCY = 20


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="评估 YOLO 声呐检测器并写 ml/yolo/metrics.json")
    p.add_argument("--weights", default=str(DEFAULT_WEIGHTS))
    p.add_argument("--data", default=str(DEFAULT_DATA))
    p.add_argument("--device", default="cpu", help="验证集评估设备（cpu/0/...）；CPU 耗时单测固定 cpu")
    p.add_argument("--n-latency", type=int, default=N_LATENCY)
    args = p.parse_args(argv)

    weights = Path(args.weights)
    if not weights.is_file():
        print(f"[eval] 权重不存在: {weights}——未写 metrics.json（先完成训练，见 ml/yolo/train.md）")
        return 1
    if not Path(args.data).is_file():
        print(f"[eval] 数据集配置不存在: {args.data}——先运行 gen_dataset")
        return 1

    from ultralytics import YOLO

    model = YOLO(str(weights))
    print(f"[eval] 在 {args.data} val 集上评估（device={args.device}）...")
    m = model.val(data=str(args.data), split="val", device=args.device, verbose=False)

    # 各类召回：DetMetrics.class_result(i) -> (p, r, ap50, ap)
    names = dict(model.names or {})
    recall: dict[str, float] = {}
    for i in range(len(names)):
        r = m.box.class_result(i)[1]
        name = names.get(i, str(i))
        recall[str(name)] = round(float(r), 4)

    # CPU 平均耗时：val 集图像连续推理 N 张（先预热 1 张）
    from ml.yolo.infer import SonarDetector

    detector = SonarDetector(weights=str(weights), conf=0.25)
    import cv2

    from ultralytics.data.utils import check_det_dataset

    data = check_det_dataset(str(args.data))
    val_img_dir = Path(data["val"])
    im_files = sorted(val_img_dir.glob("*.png")) + sorted(val_img_dir.glob("*.jpg"))
    if not im_files:
        print(f"[eval] val 目录无图像: {val_img_dir}")
        return 1
    sample = (im_files * (args.n_latency // len(im_files) + 1))[: max(args.n_latency, 1)]
    imgs = [cv2.imread(str(f), cv2.IMREAD_GRAYSCALE) for f in sample]
    detector.detect(imgs[0])  # 预热
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
    print(f"[eval] 已写入 {METRICS_PATH}")
    ok = metrics["mAP50"] >= 0.8 and metrics["cpu_ms_per_image"] < 100
    print(f"[eval] 验收线（mAP50>=0.8 且 CPU<100ms）: {'通过' if ok else '未通过，先检查标注框'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
