import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

import cv2
from ultralytics import YOLO

PROJECT_DIR = Path(__file__).resolve().parents[2]
MODEL_PATH = Path(os.getenv("YOLO_MODEL_PATH", PROJECT_DIR / "yolov8n.pt"))


class DetectionService:
    def __init__(self):
        if MODEL_PATH.exists():
            self.model = YOLO(str(MODEL_PATH))
            self.model.to('cpu')
            return

        # Kept as a fallback for local development. Production should include yolov8n.pt
        # at the project root (or set YOLO_MODEL_PATH) so Render does not need a download.
        self.model = YOLO("yolov8n.pt")
        if getattr(self.model, "ckpt_path", None):
            source = Path(self.model.ckpt_path)
            if source.exists() and not MODEL_PATH.exists():
                MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, MODEL_PATH)
                self.model = YOLO(str(MODEL_PATH))
        self.model.to('cpu')

    def detect_image(self, image_path: str) -> Dict[str, Any]:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Unable to read uploaded image file.")

        results = self.model(image, imgsz=640, verbose=False)[0]
        annotated = results.plot()
        detections = self._extract_detections(results)
        stats = self._summarize_detections(detections)

        output_path = self._save_output(image_path, annotated, "image")
        return {
            "output_path": output_path,
            "detections": detections,
            "stats": stats,
            "count": len(detections),
            "risk": {
                "risk_score": stats.get("risk_score", 0),
                "risk_level": stats.get("risk_level", "LOW"),
                "reason": stats.get("risk_reason", "No significant risk detected."),
            },
        }
