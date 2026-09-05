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

    def detect_image(self, image_path: str) -> Dict[str, Any]:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Unable to read uploaded image file.")

        results = self.model(image, verbose=False)[0]
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

    def detect_video(self, video_path: str) -> Dict[str, Any]:
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("The uploaded video could not be opened.")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

        output_dir = Path(__file__).resolve().parent.parent / "data" / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"processed_{Path(video_path).stem}.mp4"

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        if not writer.isOpened():
            raise ValueError("Unable to initialize video writer for processed output.")

        timestamps = []
        total_objects = 0
        total_persons = 0
        total_vehicles = 0
        conf_values = []
        sample_interval = max(1, int(round(fps)))

        frame_index = 0
        while True:
            success, frame = cap.read()
            if not success:
                break

            if frame_index % sample_interval == 0:
                results = self.model(frame, verbose=False, conf=0.25)[0]
                annotated = results.plot()
                detections = self._extract_detections(results)
                stats = self._summarize_detections(detections)
                writer.write(annotated)

                timestamps.append({
                    "timestamp": self._format_timestamp(frame_index / fps),
                    "count": len(detections),
                    "stats": stats,
                })
                total_objects += stats.get("total_objects", 0)
                total_persons += stats.get("persons", 0)
                total_vehicles += stats.get("vehicles", 0)
                conf_values.extend(stats.get("confidence_values", []))

            frame_index += 1

        cap.release()
        writer.release()

        if not timestamps:
            raise ValueError("No frames were analyzed from the uploaded video.")

        aggregate = {
            "total_objects": total_objects,
            "persons": total_persons,
            "vehicles": total_vehicles,
            "avg_confidence": sum(conf_values) / len(conf_values) if conf_values else 0.0,
            "density": min(100.0, total_objects / max(1, len(timestamps)) * 12.5),
            "activity_level": min(100.0, (total_persons + total_vehicles) / max(1, len(timestamps)) * 16.0),
        }

        risk = self._calculate_risk_from_stats(aggregate)
        peak = self._find_peak_risk(timestamps)
        output = {
            "output_path": str(output_path),
            "timeline": timestamps,
            "peak_risk": peak,
            "risk": risk,
            "stats": aggregate,
            "frame_count": frame_index,
            "processed_frames": len(timestamps),
        }

        return output

    def _extract_detections(self, results) -> List[Dict[str, Any]]:
        detections = []
        for box in results.boxes:
            xyxy = box.xyxy[0].tolist()
            cls = int(box.cls[0].item())
            label = results.names.get(cls, "object")
            conf = float(box.conf[0].item())
            detections.append({
                "label": label,
                "confidence": round(conf, 3),
                "x1": round(xyxy[0], 2),
                "y1": round(xyxy[1], 2),
                "x2": round(xyxy[2], 2),
                "y2": round(xyxy[3], 2),
            })
        return detections

    def _summarize_detections(self, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(detections)
        persons = sum(1 for item in detections if item["label"] == "person")
        vehicles = sum(1 for item in detections if item["label"] in {"car", "truck", "bus", "motorcycle", "bicycle"})
        confidence_values = [item["confidence"] for item in detections]
        avg_conf = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
        density = min(100.0, total * 4.5)
        activity = min(100.0, (persons * 12.0) + (vehicles * 9.0))

        risk = self._calculate_risk_from_stats({
            "total_objects": total,
            "persons": persons,
            "vehicles": vehicles,
            "avg_confidence": avg_conf,
            "density": density,
            "activity_level": activity,
        })

        return {
            "total_objects": total,
            "persons": persons,
            "vehicles": vehicles,
            "avg_confidence": round(avg_conf, 3),
            "confidence_values": confidence_values,
            "density": round(density, 2),
            "activity_level": round(activity, 2),
            "risk_score": risk["risk_score"],
            "risk_level": risk["risk_level"],
            "risk_reason": risk["reason"],
        }

    def _calculate_risk_from_stats(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        from backend.services.risk_service import calculate_risk
        return calculate_risk(stats)

    def _save_output(self, original_file: str, annotated: Any, kind: str) -> str:
        output_dir = Path(__file__).resolve().parent.parent / "data" / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(original_file).stem
        output_path = output_dir / f"{stem}_{kind}_annotated.jpg"
        cv2.imwrite(str(output_path), annotated)
        return f"/outputs/{output_path.name}"

    def _format_timestamp(self, seconds: float) -> str:
        mm, ss = divmod(int(seconds), 60)
        hh, mm = divmod(mm, 60)
        return f"{hh:02d}:{mm:02d}:{ss:02d}"

    def _find_peak_risk(self, timestamps: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not timestamps:
            return {"timestamp": "00:00:00", "risk_score": 0, "risk_level": "LOW"}

        peak = max(timestamps, key=lambda item: self._calculate_risk_from_stats(item["stats"])["risk_score"])
        risk = self._calculate_risk_from_stats(peak["stats"])
        return {
            "timestamp": peak["timestamp"],
            "risk_score": risk["risk_score"],
            "risk_level": risk["risk_level"],
            "reason": risk["reason"],
        }
