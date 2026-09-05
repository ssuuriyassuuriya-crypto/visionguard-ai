import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.database.db import get_connection
from backend.services.detection_service import DetectionService
from backend.services.risk_service import build_risk_timeline

router = APIRouter()

detection_service = DetectionService()
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def add_history_entry(filename: str, media_type: str, detection_count: int, risk_score: int, risk_level: str, peak_timestamp: str | None, output_path: str, stats: dict, source_path: str):
    created_at = datetime.utcnow().isoformat()
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO history (filename, created_at, media_type, detection_count, risk_score, risk_level, peak_timestamp, output_path, stats, source_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            filename,
            created_at,
            media_type,
            int(detection_count),
            int(risk_score),
            risk_level,
            peak_timestamp,
            output_path,
            json.dumps(stats),
            source_path,
        ),
    )
    conn.commit()
    history_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
    conn.close()
    return history_id


@router.get("/api/health")
def health_check():
    return {"status": "ok", "service": "VisionGuard AI", "timestamp": datetime.utcnow().isoformat()}


@router.post("/api/analyze/image")
async def analyze_image(file: UploadFile = File(...)):
    allowed = {"image/jpeg", "image/jpg", "image/png"}
    if file.content_type not in allowed and not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        raise HTTPException(status_code=400, detail="Unsupported image type. Please upload JPG, JPEG, or PNG.")

    filename = file.filename or "uploaded_image"
    target = UPLOAD_DIR / filename
    with open(target, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = detection_service.detect_image(str(target))
    stats = result["stats"]
    stats["risk_score"] = result["risk"]["risk_score"]
    stats["risk_level"] = result["risk"]["risk_level"]
    stats["risk_reason"] = result["risk"]["reason"]

    history_id = add_history_entry(
        filename=filename,
        media_type="image",
        detection_count=int(result["count"]),
        risk_score=int(result["risk"]["risk_score"]),
        risk_level=result["risk"]["risk_level"],
        peak_timestamp=None,
        output_path=result["output_path"],
        stats=stats,
        source_path=str(target),
    )

    return {
        "id": history_id,
        "filename": filename,
        "media_type": "image",
        "output_path": result["output_path"],
        "detections": result["detections"],
        "count": result["count"],
        "stats": stats,
        "risk": result["risk"],
    }


@router.post("/api/analyze/video")
async def analyze_video(file: UploadFile = File(...)):
    allowed = {"video/mp4", "video/avi", "video/quicktime", "video/x-msvideo"}
    if file.content_type not in allowed and not file.filename.lower().endswith((".mp4", ".avi", ".mov")):
        raise HTTPException(status_code=400, detail="Unsupported video type. Please upload MP4, AVI, or MOV.")

    filename = file.filename or "uploaded_video"
    target = UPLOAD_DIR / filename
    with open(target, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = detection_service.detect_video(str(target))
    timeline = build_risk_timeline(result["timeline"])
    peak = result["peak_risk"]
    if timeline:
        peak = max(timeline, key=lambda item: item["risk_score"])

    stats = result["stats"]
    stats["risk_score"] = result["risk"]["risk_score"]
    stats["risk_level"] = result["risk"]["risk_level"]
    stats["risk_reason"] = result["risk"]["reason"]

    history_id = add_history_entry(
        filename=filename,
        media_type="video",
        detection_count=int(stats.get("total_objects", 0)),
        risk_score=int(result["risk"]["risk_score"]),
        risk_level=result["risk"]["risk_level"],
        peak_timestamp=peak.get("timestamp", "00:00:00"),
        output_path=result["output_path"],
        stats=stats,
        source_path=str(target),
    )

    return {
        "id": history_id,
        "filename": filename,
        "media_type": "video",
        "output_path": result["output_path"],
        "timeline": timeline,
        "peak_risk": peak,
        "risk": result["risk"],
        "stats": stats,
    }


@router.get("/api/history")
def get_history():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM history ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@router.get("/api/history/{item_id}")
def get_history_item(item_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM history WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="History item not found.")
    return dict(row)


@router.delete("/api/history/{item_id}")
def delete_history_item(item_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM history WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="History item not found.")

    if row["output_path"] and os.path.exists(row["output_path"]):
        os.remove(row["output_path"])
    if row["source_path"] and os.path.exists(row["source_path"]):
        os.remove(row["source_path"])

    conn.execute("DELETE FROM history WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"deleted": True, "id": item_id}
