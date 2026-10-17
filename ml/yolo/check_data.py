"""ml/yolo/check_data.py —— 训练前数据自检（C2）。

用 Ultralytics **实际数据加载器**验证 sonar.yaml：
1. check_det_dataset：与训练同一套解析逻辑（路径解析/目录存在性检查）；
2. build_yolo_dataset：逐张读取并解析全部标签文件，统计可用图像数。

预期（seed=0 全量数据）：train 3400 张、val 600 张。
用法：在仓库根目录运行  python ml/yolo/check_data.py
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
    data = check_det_dataset(data_yaml)  # 训练用的同一条解析链路
    print(f"[check] yaml 解析 OK: train={data['train']}  val={data['val']}")
    print(f"[check] 类别: {data['names']}")

    ok = True
    for split, expect in (("train", 3400), ("val", 600)):
        ds = build_yolo_dataset(cfg, img_path=data[split], batch=16, data=data, mode=split)
        n = len(ds.im_files)
        empty = sum(1 for lb in ds.labels if len(lb.get("segments", [])) == 0 and len(lb.get("bboxes", [])) == 0)
        print(f"[check] {split}: 加载 {n} 张（预期 {expect}），其中负样本(空标签) {empty} 张")
        if n != expect:
            ok = False
    print(f"[check] 结果: {'通过' if ok else '数量与预期不符，先检查数据集生成'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(count())
