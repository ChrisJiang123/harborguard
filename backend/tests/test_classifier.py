from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from backend.app import config
from backend.app.perception.classifier import SonarClassifier

TARGET = {"cls": "uuv", "range_m": 100, "bearing_deg": 0, "length_m": 6, "width_m": 2, "aspect_deg": 0}


def test_missing_c_modules_and_weights_use_reproducible_stub_png(tmp_path):
    classifier = SonarClassifier(weights=tmp_path / "missing.pt")
    result = classifier.classify([TARGET], seed=42)
    again = classifier.classify([TARGET], seed=42)
    assert result == again
    assert result["model"] == "stub"
    assert result["detections"][0]["cls"] == "uuv"
    assert 0.7 <= result["detections"][0]["conf"] <= 0.9
    x1, y1, x2, y2 = result["detections"][0]["bbox"]
    assert 0 <= x1 < x2 < config.SONAR_SIZE
    assert 0 <= y1 < y2 < config.SONAR_SIZE
    image = Image.open(BytesIO(result["image"]))
    assert image.size == (config.SONAR_SIZE, config.SONAR_SIZE)
    assert image.format == "PNG"


def test_c_renderer_and_detector_are_called_with_frozen_contract():
    calls = []
    def render(targets, **kwargs):
        calls.append((targets, kwargs))
        return np.zeros((config.SONAR_SIZE, config.SONAR_SIZE), dtype=np.uint8), [{"cls": "uuv", "bbox": [10, 20, 30, 40]}]
    class Detector:
        def detect(self, image):
            assert image.ndim == 2
            return [{"cls": "uuv", "conf": 0.92, "bbox": [10, 20, 30, 40]}]
    result = SonarClassifier(renderer=render, detector=Detector()).classify([TARGET], seed=7)
    assert result["model"] == "yolo26n"
    assert result["detections"] == [{"cls": "uuv", "conf": 0.92, "bbox": [10, 20, 30, 40]}]
    assert calls[0][1] == {"max_range_m": config.PING_RANGE_M, "fov_deg": config.SONAR_FOV_DEG,
                           "noise": config.SONAR_NOISE, "seed": 7, "size": config.SONAR_SIZE}


def test_broken_c_components_fail_closed_to_stub():
    def broken_renderer(*args, **kwargs):
        raise RuntimeError("renderer unavailable")
    class BrokenDetector:
        def detect(self, image):
            raise FileNotFoundError("weight file missing")
    result = SonarClassifier(renderer=broken_renderer, detector=BrokenDetector()).classify([TARGET], seed=3)
    assert result["model"] == "stub"
    assert len(result["detections"]) == 1


def test_stub_does_not_detect_objects_outside_ping_fov():
    result = SonarClassifier().classify([dict(TARGET, bearing_deg=90), dict(TARGET, range_m=1000)], seed=1)
    assert result["detections"] == []


def test_renderer_fallback_is_labeled_stub_even_when_detector_exists():
    def broken_renderer(*args, **kwargs):
        raise RuntimeError("renderer failed")
    class Detector:
        def detect(self, image):
            raise AssertionError("Do not present inference over synthetic fallback as real sonar")
    result = SonarClassifier(renderer=broken_renderer, detector=Detector()).classify([TARGET], seed=3)
    assert result["model"] == "stub"
    assert result["detections"][0]["cls"] == "uuv"


@pytest.mark.parametrize("invalid", [
    {"cls": "uuv", "conf": 0.8, "bbox": ["x", 20, 30, 40]},
    {"cls": "uuv", "conf": 0.8, "bbox": [float("nan"), 20, 30, 40]},
    {"cls": "uuv", "conf": float("nan"), "bbox": [10, 20, 30, 40]},
    {"cls": "uuv", "conf": 0.8, "bbox": [30, 20, 10, 40]},
])
def test_malformed_c_numeric_output_falls_back_before_drawing(invalid):
    def renderer(*args, **kwargs):
        return np.zeros((config.SONAR_SIZE, config.SONAR_SIZE), dtype=np.uint8), [{"cls": "uuv", "bbox": [10, 20, 30, 40]}]
    class Detector:
        def detect(self, image):
            return [invalid]
    result = SonarClassifier(renderer=renderer, detector=Detector()).classify([TARGET], seed=2)
    assert result["model"] == "stub"
    assert Image.open(BytesIO(result["image"])).format == "PNG"
    assert result["detections"][0]["bbox"] == [10, 20, 30, 40]
