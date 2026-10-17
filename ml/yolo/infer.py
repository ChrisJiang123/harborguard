"""ml.yolo.infer —— SonarDetector 推理接口（C2，共享契约 v1 §7，签名一字不改）。

B 在后端 import（backend/app/perception/classifier.py）：
- 构造时加载一次权重并**强制 CPU** 推理；
- detect 输入灰度图（内部转三通道），返回 [{"cls": str, "conf": float, "bbox": [x1,y1,x2,y2]}]；
- 权重文件不存在时抛 FileNotFoundError（明确信息），B 捕获后自动改用桩，不伪造预测。
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

# YOLO 类别 ID（共享契约）：0 uuv，1 fish_school，2 debris，3 marine_mammal
CLASS_NAMES: tuple[str, ...] = ("uuv", "fish_school", "debris", "marine_mammal")


class SonarDetector:
    """契约签名::

        def __init__(self, weights: str = "ml/yolo/weights/best.pt", conf: float = 0.25)
        def detect(self, img: "np.ndarray") -> list[dict]
    """

    def __init__(self, weights: str = "ml/yolo/weights/best.pt", conf: float = 0.25):
        w = Path(weights)
        if not w.is_file():
            raise FileNotFoundError(
                f"YOLO 声呐权重不存在: {w}——先完成训练得到 best.pt 并放入 ml/yolo/weights/（见 ml/yolo/train.md）"
            )
        from ultralytics import YOLO  # 延迟导入：无权重时 import 本模块不应要求 torch

        self._model = YOLO(str(w))
        self.conf = float(conf)
        self._names = dict(getattr(self._model, "names", {}) or {})

    def detect(self, img: "np.ndarray") -> list[dict]:
        arr = np.asarray(img)
        if arr.ndim == 2:  # 灰度 → 三通道
            arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
        elif arr.ndim == 3 and arr.shape[2] == 3:
            pass
        elif arr.ndim == 3 and arr.shape[2] == 4:
            arr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
        else:
            raise ValueError(f"detect 需要 HxW 或 HxWx3/4 图像，收到 shape={arr.shape}")

        # 强制 CPU（任务书 C2：每张 < 100 ms 的 CPU 检测器）
        results = self._model.predict(arr, device="cpu", conf=self.conf, verbose=False)
        out: list[dict] = []
        for box in results[0].boxes:
            cls_id = int(box.cls.item())
            name = (
                CLASS_NAMES[cls_id] if 0 <= cls_id < len(CLASS_NAMES)
                else self._names.get(cls_id, str(cls_id))
            )
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
            out.append({
                "cls": name,
                "conf": float(box.conf.item()),
                "bbox": [int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))],
            })
        return out
