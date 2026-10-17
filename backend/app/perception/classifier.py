"""Optional C renderer/YOLO adapter with a reproducible self-contained fallback."""
from __future__ import annotations

import math
import time
from importlib import import_module
from io import BytesIO
from numbers import Real
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .. import config

SONAR_CLASSES = {"uuv", "fish_school", "debris", "marine_mammal"}


def sonar_pixel(distance, bearing_deg=0.0, *, projection="stub_linear"):
    """B-private projection matching the renderer actually used for this image.

    C fits the entire fan in the square; B's fallback uses the full height.
    The detector/model label alone cannot distinguish these two image layouts.
    """
    size = config.SONAR_SIZE
    radius = size-1
    center = size/2
    if projection == "c_fan":
        radius = min(radius, (size/2-1)/math.sin(math.radians(config.SONAR_FOV_DEG)/2))
        center = (size-1)/2
    theta = math.radians(bearing_deg)
    radial = distance/config.PING_RANGE_M*radius
    return center+radial*math.sin(theta), size-1-radial*math.cos(theta)


def _validated_result(item, *, confidence=False):
    """Validate plugin output before it can reach Pillow or public models."""
    cls, box = item["cls"], item["bbox"]
    if cls not in SONAR_CLASSES or len(box) != 4:
        raise ValueError("Invalid sonar class or box shape")
    if any(not isinstance(value, Real) or not math.isfinite(value) for value in box):
        raise ValueError("Sonar boxes require finite numeric coordinates")
    box = [float(np.clip(value, 0, config.SONAR_SIZE - 1)) for value in box]
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("Sonar boxes must have positive width and height")
    result = {"cls": cls, "bbox": box}
    if confidence:
        conf = item["conf"]
        if not isinstance(conf, Real) or not math.isfinite(conf) or not 0 <= conf <= 1:
            raise ValueError("Sonar confidence must be finite and between zero and one")
        result["conf"] = float(conf)
    return result


class SonarClassifier:
    """classify(renderer_targets, seed) -> model, PNG image bytes, detections.

    Targets follow C's render_ping keyword contract. Detections use contract
    corner boxes [x1,y1,x2,y2]. Optional imports/inference cannot stop simulation.
    """

    def __init__(self, weights=None, *, renderer=None, detector=None):
        self.renderer = renderer
        self.detector = detector
        self.last_error: str | None = None
        self._warmup_result = None
        if self.renderer is None:
            try:
                self.renderer = import_module("ml.sonar.render").render_ping
            except Exception as error:  # noqa: BLE001 - Optional C plugin must not stop the backend.
                self.last_error = str(error)
        if self.detector is None:
            weights = Path(weights or config.SONAR_WEIGHTS_PATH)
            try:
                if not weights.is_file():
                    raise FileNotFoundError(f"Sonar weights absent: {weights}")
                self.detector = import_module("ml.yolo.infer").SonarDetector(weights=str(weights), conf=config.DETECTION_MIN_CONF)
            except Exception as error:  # noqa: BLE001 - Missing/incompatible third-party model fallback.
                self.last_error = str(error)

    def warmup(self):
        """Prime CPU inference before readiness, without touching world RNG/events."""
        if self._warmup_result is None:
            begin = time.perf_counter()
            model = self.classify([], seed=0)["model"] if self.detector is not None else "stub"
            self._warmup_result = {"model": model, "ms": (time.perf_counter()-begin)*1000}
        return dict(self._warmup_result)

    @property
    def survey_min_range_m(self):
        # C's polar fan is degenerate at its origin. The self-contained B
        # fallback has its own rectangular pixel support, tested at zero range.
        return config.DISASTER_MIN_RANGE_M if self.renderer is not None else 0.0

    def _stub_render(self, targets, rng):
        size = config.SONAR_SIZE
        image = np.clip(rng.normal(36, config.STUB_PIXEL_NOISE_STD, (size, size)), 0, 255).astype(np.uint8)
        annotations = []
        for target in targets:
            distance = float(target.get("range_m", config.PING_RANGE_M / 2))
            bearing = float(target.get("bearing_deg", 0))
            if target.get("cls") not in SONAR_CLASSES or not 0 <= distance <= config.PING_RANGE_M or abs(bearing) > config.SONAR_FOV_DEG / 2:
                continue
            radians = math.radians(bearing)
            scale = (size - 1) / config.PING_RANGE_M
            cx = size / 2 + math.sin(radians) * distance * scale
            cy = size - 1 - math.cos(radians) * distance * scale
            half_width = max(3, float(target.get("width_m", 2)) * scale / 2)
            half_length = max(5, float(target.get("length_m", 5)) * scale / 2)
            bbox = [int(np.clip(cx - half_width, 0, size - 2)), int(np.clip(cy - half_length, 0, size - 2)),
                    int(np.clip(cx + half_width, 1, size - 1)), int(np.clip(cy + half_length, 1, size - 1))]
            image[bbox[1]:bbox[3], bbox[0]:bbox[2]] = 255
            annotations.append({"cls": target["cls"], "bbox": bbox})
        return image, annotations

    def classify(self, targets: list[dict], seed: int = 0):
        rng = np.random.default_rng(seed)
        valid_targets = [dict(target) for target in targets if target.get("cls") in SONAR_CLASSES]
        rendered_by_c = False
        try:
            if self.renderer is None:
                raise ImportError("C sonar renderer unavailable")
            image, annotations = self.renderer(valid_targets, max_range_m=config.PING_RANGE_M, fov_deg=config.SONAR_FOV_DEG,
                                               noise=config.SONAR_NOISE, seed=int(seed), size=config.SONAR_SIZE)
            image = np.asarray(image)
            if image.dtype != np.uint8 or image.ndim != 2 or image.shape != (config.SONAR_SIZE, config.SONAR_SIZE):
                raise ValueError("C renderer returned an invalid grayscale image")
            annotations = [_validated_result(annotation) for annotation in annotations]
            rendered_by_c = True
        except Exception as error:  # noqa: BLE001 - External renderer is an explicit fault boundary.
            self.last_error = str(error)
            image, annotations = self._stub_render(valid_targets, rng)
        model = "stub"
        try:
            if self.detector is None or not rendered_by_c:
                raise ImportError("C sonar renderer/detector unavailable; use full stub pipeline")
            detections = [_validated_result(detection, confidence=True) for detection in self.detector.detect(image)]
            model = "yolo26n"
        except Exception as error:  # noqa: BLE001 - External inference is an explicit fault boundary.
            self.last_error = str(error)
            detections = [{"cls": annotation["cls"], "bbox": annotation["bbox"],
                           "conf": float(rng.uniform(*config.STUB_CONFIDENCE_RANGE))} for annotation in annotations]
        pil = Image.fromarray(image).convert("RGB")
        draw = ImageDraw.Draw(pil)
        normalized = []
        for detection in detections:
            bbox = [float(np.clip(v, 0, config.SONAR_SIZE - 1)) for v in detection["bbox"]]
            if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
                continue
            normalized.append({"cls": detection["cls"], "conf": float(detection["conf"]), "bbox": bbox})
            draw.rectangle(bbox, outline="lime", width=2)
            draw.text((bbox[0], max(0, bbox[1] - 12)), f"{detection['cls']} {float(detection['conf']):.2f}", fill="lime")
        buffer = BytesIO()
        pil.save(buffer, format="PNG", compress_level=config.SONAR_PNG_COMPRESSION_LEVEL)
        return {"model": model, "image": buffer.getvalue(), "detections": normalized,
                "_projection": "c_fan" if rendered_by_c else "stub_linear"}

    render_and_classify = classify
