"""
vision/object_detector.py
==========================
Object detection using YOLOv8 (ultralytics).
Returns list of detected class names.
"""

from __future__ import annotations
import os

_model = None
MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "uploads/yolov8n.pt")   # local model file


def _get_model():
    global _model
    if _model is None:
        try:
            from ultralytics import YOLO
            import os
            path = MODEL_PATH if os.path.exists(MODEL_PATH) else "yolov8n.pt"
            _model = YOLO(path)
            print(f"[ObjectDetector] YOLO model loaded from {path}")
        except ImportError:
            print("[ObjectDetector] ultralytics not installed.")
        except Exception as e:
            print(f"[ObjectDetector] Model load error: {e}")
    return _model


def detect_objects(image_path: str, confidence: float = 0.4) -> list[str]:
    """Returns deduplicated list of detected object class names."""
    model = _get_model()
    if model is None:
        return []
    try:
        results = model(image_path, conf=confidence, verbose=False, device="cpu")
        names = []
        for result in results:
            for cls_id in result.boxes.cls.tolist():
                name = result.names[int(cls_id)]
                if name not in names:
                    names.append(name)
        return names
    except Exception as e:
        print(f"[ObjectDetector] Error on {image_path}: {e}")
        return []
