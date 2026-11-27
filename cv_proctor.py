"""Computer Vision & Academic Integrity Proctoring Engine.

Supports:
1. Optional OpenCV (cv2) Haar-cascade face count & brightness verification when installed
2. Client-side CV telemetry validation (skin/luminance face clustering, gaze offset, motion, occlusion)
3. Integrity score computation & risk classification
4. Flagged snapshot persistence for faculty audit
"""

from __future__ import annotations

import base64
import logging
import os
import time
from threading import Lock
from pathlib import Path
from typing import Any

from backend.config import (
    INTEGRITY_PASS_THRESHOLD,
    SEVERITY_BY_EVENT,
    UPLOAD_DIR,
    VIOLATION_PENALTIES,
    WARNING_TRIGGER_EVENTS,
)

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore

    _FACE_CASCADE = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    HAS_OPENCV = True
except Exception:  # pragma: no cover - optional dependency
    cv2 = None
    np = None
    _FACE_CASCADE = None
    HAS_OPENCV = False


_DEVICE_LOCK = Lock()
_DEVICE_MODEL = None
_COCO_DEVICES = {73: "laptop", 77: "cell phone"}


def load_device_detector() -> bool:
    global _DEVICE_MODEL
    weights = os.environ.get("EXAM_DEVICE_MODEL")
    config = os.environ.get("EXAM_DEVICE_CONFIG")
    if not (weights or config):
        return False
    if not (HAS_OPENCV and weights and config):
        logging.warning("Device detection requires OpenCV and both model paths.")
        return False
    with _DEVICE_LOCK:
        if _DEVICE_MODEL is None:
            try:
                model = cv2.dnn_DetectionModel(weights, config)
                model.setInputParams(size=(300, 300), swapRB=True)
                _DEVICE_MODEL = model
            except cv2.error:
                logging.exception("Unable to load the SSD MobileNet COCO model.")
                return False
    return True


def device_detection_enabled() -> bool:
    return _DEVICE_MODEL is not None


def _detect_device(frame) -> tuple[str, float]:
    if _DEVICE_MODEL is None:
        return "", 0.0
    try:
        with _DEVICE_LOCK:
            classes, scores, _ = _DEVICE_MODEL.detect(frame, confThreshold=0.65, nmsThreshold=0.4)
        return max(
            ((_COCO_DEVICES[int(label)], float(score))
             for label, score in zip(classes, scores) if int(label) in _COCO_DEVICES),
            key=lambda item: item[1],
            default=("", 0.0),
        )
    except cv2.error:
        logging.exception("Device detection failed.")
        return "", 0.0


def analyze_snapshot_with_opencv(image_b64: str) -> dict[str, Any] | None:
    """Run OpenCV face & brightness analysis on a base64 image if cv2 is installed."""
    if not HAS_OPENCV or not image_b64:
        return None
    try:
        payload = image_b64.split(",", 1)[1] if "," in image_b64 else image_b64
        raw = base64.b64decode(payload)
        arr = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_luma = float(gray.mean())
        faces = _FACE_CASCADE.detectMultiScale(
            gray, scaleFactor=1.15, minNeighbors=5, minSize=(40, 40)
        )
        face_count = int(len(faces))
        h, w = gray.shape[:2]
        offset_x = 0.0
        if face_count == 1:
            fx, fy, fw, fh = faces[0]
            cx = (fx + fw / 2.0) / max(1, w)
            offset_x = abs(cx - 0.5)
        object_label, object_score = _detect_device(frame) if mean_luma >= 22 else ("", 0.0)
        return {
            "object_label": object_label,
            "object_score": object_score,
            "engine": "OPENCV_HAAR",
            "face_count": face_count,
            "mean_brightness": round(mean_luma, 2),
            "center_offset_x": round(offset_x, 3),
        }
    except Exception:
        return None


def save_snapshot_if_flagged(attempt_id: int, event_type: str, image_b64: str | None) -> str | None:
    """Persist base64 JPEG/PNG snapshot for flagged proctoring events."""
    if not image_b64:
        return None
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        ext = "jpg"
        payload = image_b64
        if image_b64.startswith("data:image/png"):
            ext = "png"
        if "," in image_b64:
            payload = image_b64.split(",", 1)[1]
        raw = base64.b64decode(payload, validate=True)
        signature = b"\x89PNG\r\n\x1a\n" if ext == "png" else b"\xff\xd8\xff"
        if not raw.startswith(signature):
            return None
        # Guard snapshot size (<= 1.5 MB)
        if len(raw) > 1_500_000 or len(raw) < 100:
            return None
        filename = f"attempt_{attempt_id}_{int(time.time() * 1000)}_{event_type.lower()}.{ext}"
        target = UPLOAD_DIR / filename
        target.write_bytes(raw)
        return f"/proctor_snapshots/{filename}"
    except Exception:
        return None


def evaluate_cv_telemetry(
    metrics: dict[str, Any],
    snapshot_b64: str | None = None,
) -> dict[str, Any]:
    """Infer proctoring events from CV frame metrics (with OpenCV verification if available)."""
    cv_override = analyze_snapshot_with_opencv(snapshot_b64) if snapshot_b64 else None

    face_count = int(
        cv_override["face_count"]
        if cv_override is not None
        else metrics.get("face_count", 1)
    )
    brightness = float(
        cv_override["mean_brightness"]
        if cv_override is not None
        else metrics.get("mean_brightness", 110.0)
    )
    center_offset_x = float(
        cv_override["center_offset_x"]
        if cv_override is not None
        else metrics.get("center_offset_x", 0.0)
    )
    motion_score = float(metrics.get("motion_score", 0.0))

    detected_events: list[dict[str, Any]] = []

    if brightness < 22.0:
        detected_events.append({
            "event_type": "CAMERA_OCCLUDED",
            "severity": SEVERITY_BY_EVENT["CAMERA_OCCLUDED"],
            "details": f"Camera feed unusually dark (brightness={brightness:.1f}/255).",
        })
    elif face_count == 0:
        detected_events.append({
            "event_type": "NO_FACE",
            "severity": SEVERITY_BY_EVENT["NO_FACE"],
            "details": "No candidate face detected in webcam frame.",
        })
    elif face_count > 1:
        detected_events.append({
            "event_type": "MULTIPLE_FACES",
            "severity": SEVERITY_BY_EVENT["MULTIPLE_FACES"],
            "details": f"Multiple faces detected in frame (count={face_count}).",
        })
    elif center_offset_x > 0.24:
        detected_events.append({
            "event_type": "LOOKING_AWAY",
            "severity": SEVERITY_BY_EVENT["LOOKING_AWAY"],
            "details": f"Head/gaze shifted significantly off-center (offset={center_offset_x:.2f}).",
        })

    if motion_score > 0.32 and brightness >= 22.0:
        detected_events.append({
            "event_type": "SUSPICIOUS_MOTION",
            "severity": SEVERITY_BY_EVENT["SUSPICIOUS_MOTION"],
            "details": f"High sudden movement detected in frame (motion={motion_score:.2f}).",
        })

    object_metrics = cv_override if _DEVICE_MODEL is not None and cv_override else metrics
    object_label = (object_metrics.get("object_label") or "").strip()
    object_score = float(object_metrics.get("object_score", 0.0))
    if (object_metrics.get("object_detected") or object_score >= 0.65) and brightness >= 22.0:
        desc = object_label or "Unauthorized electronic device / rectangular object"
        detected_events.append({
            "event_type": "UNAUTHORIZED_OBJECT",
            "severity": SEVERITY_BY_EVENT["UNAUTHORIZED_OBJECT"],
            "details": f"Object detection alert: {desc} detected in camera view (score={object_score:.2f}).",
        })

    return {
        "engine": cv_override["engine"] if cv_override else metrics.get("engine", "WEBRTC_CANVAS_CV"),
        "face_count": face_count,
        "mean_brightness": round(brightness, 2),
        "center_offset_x": round(center_offset_x, 3),
        "motion_score": round(motion_score, 3),
        "object_score": round(object_score, 3),
        "detected_events": detected_events,
    }


def compute_integrity_summary(events: list[dict[str, Any]], strictness: str = "MEDIUM") -> dict[str, Any]:
    """Compute overall academic integrity score (0-100) and risk status from logged events."""
    multiplier = {"LOW": 0.7, "MEDIUM": 1.0, "HIGH": 1.3}.get((strictness or "MEDIUM").upper(), 1.0)

    total_penalty = 0.0
    counts_by_type: dict[str, int] = {}
    high_severity_count = 0
    warning_count = 0

    for ev in events:
        etype = (ev.get("event_type") or "").upper()
        if etype in ("HEARTBEAT_OK", "EXAM_STARTED", "EXAM_SUBMITTED"):
            continue
        counts_by_type[etype] = counts_by_type.get(etype, 0) + 1
        base_penalty = VIOLATION_PENALTIES.get(etype, 4.0)
        total_penalty += base_penalty * multiplier
        sev = (ev.get("severity") or SEVERITY_BY_EVENT.get(etype, "LOW")).upper()
        if sev == "HIGH":
            high_severity_count += 1
        if etype in WARNING_TRIGGER_EVENTS:
            warning_count += 1

    integrity_score = round(max(0.0, min(100.0, 100.0 - total_penalty)), 1)
    if integrity_score < INTEGRITY_PASS_THRESHOLD or high_severity_count >= 3:
        risk_level = "FLAGGED"
    elif integrity_score < 88.0 or sum(counts_by_type.values()) >= 2:
        risk_level = "WATCH"
    else:
        risk_level = "CLEAR"

    return {
        "integrity_score": integrity_score,
        "risk_level": risk_level,
        "total_violations": sum(counts_by_type.values()),
        "high_severity_count": high_severity_count,
        "warning_count": warning_count,
        "counts_by_type": counts_by_type,
    }
