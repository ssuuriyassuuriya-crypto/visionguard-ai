import math
from typing import Dict, List, Any


def calculate_risk(stats: Dict[str, Any]) -> Dict[str, Any]:
    total = int(stats.get("total_objects", 0) or 0)
    persons = int(stats.get("persons", 0) or 0)
    vehicles = int(stats.get("vehicles", 0) or 0)
    avg_conf = float(stats.get("avg_confidence", 0.0) or 0.0)
    density = float(stats.get("density", 0.0) or 0.0)
    activity = float(stats.get("activity_level", 0.0) or 0.0)

    risk_score = (
        total * 9
        + persons * 7
        + vehicles * 6
        + density * 24
        + activity * 20
        + avg_conf * 15
    )

    # Keep response bounded to 0..100
    risk_score = max(0, min(100, int(round(risk_score))))

    if risk_score <= 39:
        risk_level = "LOW"
    elif risk_score <= 69:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    if total == 0 and avg_conf == 0:
        reason = "No significant objects detected; the scene appears calm."
    elif risk_level == "LOW":
        reason = "Detectable activity is limited and the subject density remains low."
    elif risk_level == "MEDIUM":
        reason = "Moderate people and vehicle activity suggests elevated monitoring attention."
    else:
        reason = "Dense activity and elevated confidence indicate significant safety risk."

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reason": reason,
    }


def build_risk_timeline(samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    timeline = []
    for sample in samples:
        metrics = sample.get("stats", {})
        risk = calculate_risk(metrics)
        timeline.append(
            {
                "timestamp": sample.get("timestamp"),
                "risk_score": risk["risk_score"],
                "risk_level": risk["risk_level"],
                "reason": risk["reason"],
                "total_objects": metrics.get("total_objects", 0),
                "persons": metrics.get("persons", 0),
                "vehicles": metrics.get("vehicles", 0),
            }
        )

    if not timeline:
        return []

    peak = max(timeline, key=lambda item: item["risk_score"])
    for item in timeline:
        item["is_peak"] = item["timestamp"] == peak["timestamp"] and item["risk_score"] == peak["risk_score"]

    return timeline
