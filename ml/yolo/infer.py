"""C2 SonarDetector with frozen section7 signature, imported by B. Load weights once and force CPU.
detect converts grayscale internally to three channels and returns cls/conf/pixel bbox. Missing
weights raise FileNotFoundError for an explicit B stub fallback, never invented predictions.
"""


from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

# Frozen class IDs:0uuv,1fish_school,2debris,3marine_mammal.
CLASS_NAMES: tuple[str, ...] = ("uuv", "fish_school", "debris", "marine_mammal")


class SonarDetector:
    """Frozen signatures: __init__(weights="ml/yolo/weights/best.pt",conf=0.25); detect(img:
    np.ndarray) -> list[dict].
    """
    def __init__(self, weights: str = "ml/yolo/weights/best.pt", conf: float = 0.25):
        w = Path(weights)
        if not w.is_file():
            raise FileNotFoundError(
                f"YOLO sonar weights do not exist: {w}; train/export best.pt into ml/yolo/weights/ (see ml/yolo/train.md)"
            )
        from ultralytics import YOLO  # Lazy import avoids requiring torch when weights are absent.

        self._model = YOLO(str(w))
        self.conf = float(conf)
        self._names = dict(getattr(self._model, "names", {}) or {})

    def detect(self, img: "np.ndarray") -> list[dict]:
        arr = np.asarray(img)
        if arr.ndim == 2:  # Grayscale to three channels.
            arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
        elif arr.ndim == 3 and arr.shape[2] == 3:
            pass
        elif arr.ndim == 3 and arr.shape[2] == 4:
            arr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
        else:
            raise ValueError(f"detect requires HxW or HxWx3/4 input, received shape={arr.shape}")

        # Force CPU (C2 target:under100ms/image).
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
