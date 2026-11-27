"""Application configuration and constants."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "proctor_snapshots"
FRONTEND_DIR = BASE_DIR / "frontend"

DB_PATH = Path(os.environ.get("EXAM_DB_PATH", str(DATA_DIR / "exam_system.db")))
HOST = os.environ.get("EXAM_HOST", "127.0.0.1")
PORT = int(os.environ.get("EXAM_PORT", "8000"))

# Persistent secret key fallback (env var overrides for production deployments)
SECRET_KEY = os.environ.get(
    "EXAM_SECRET_KEY",
    "ai-automated-exam-eval-secret-key-change-in-production-2026",
)
TOKEN_TTL_SECONDS = int(os.environ.get("EXAM_TOKEN_TTL", str(60 * 60 * 12)))  # 12 hours

# NLP Evaluation thresholds
NLP_CONFIDENCE_LOW_THRESHOLD = 0.62
INTEGRITY_PASS_THRESHOLD = 70.0

# Violation penalty weights used by CV & Telemetry Integrity Scorer
VIOLATION_PENALTIES = {
    "NO_FACE": 4.5,
    "MULTIPLE_FACES": 12.0,
    "UNAUTHORIZED_OBJECT": 10.0,
    "LOOKING_AWAY": 3.0,
    "CAMERA_OCCLUDED": 8.0,
    "SUSPICIOUS_MOTION": 2.5,
    "TAB_SWITCH": 7.0,
    "WINDOW_BLUR": 5.0,
    "FULLSCREEN_EXIT": 6.0,
    "COPY_PASTE_ATTEMPT": 8.0,
    "RIGHT_CLICK_ATTEMPT": 2.0,
    "DEVTOOLS_SHORTCUT": 10.0,
    "EXTERNAL_NAVIGATION_ATTEMPT": 9.0,
}

SEVERITY_BY_EVENT = {
    "NO_FACE": "MEDIUM",
    "MULTIPLE_FACES": "HIGH",
    "UNAUTHORIZED_OBJECT": "HIGH",
    "LOOKING_AWAY": "LOW",
    "CAMERA_OCCLUDED": "HIGH",
    "SUSPICIOUS_MOTION": "LOW",
    "TAB_SWITCH": "HIGH",
    "WINDOW_BLUR": "MEDIUM",
    "FULLSCREEN_EXIT": "MEDIUM",
    "COPY_PASTE_ATTEMPT": "HIGH",
    "RIGHT_CLICK_ATTEMPT": "LOW",
    "DEVTOOLS_SHORTCUT": "HIGH",
    "EXTERNAL_NAVIGATION_ATTEMPT": "HIGH",
}

DEFAULT_MAX_WARNINGS_BY_STRICTNESS = {
    "LOW": 8,
    "MEDIUM": 5,
    "HIGH": 3,
}

# Events that increment the candidate's formal warning counter
WARNING_TRIGGER_EVENTS = {
    "MULTIPLE_FACES",
    "UNAUTHORIZED_OBJECT",
    "CAMERA_OCCLUDED",
    "NO_FACE",
    "TAB_SWITCH",
    "WINDOW_BLUR",
    "FULLSCREEN_EXIT",
    "COPY_PASTE_ATTEMPT",
    "DEVTOOLS_SHORTCUT",
    "EXTERNAL_NAVIGATION_ATTEMPT",
}
