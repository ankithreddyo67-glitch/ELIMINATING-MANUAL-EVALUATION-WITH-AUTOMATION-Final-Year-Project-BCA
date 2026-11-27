"""Unit tests for the Computer Vision & Integrity Proctoring engine."""

import unittest

from backend.cv_proctor import compute_integrity_summary, evaluate_cv_telemetry


class TestCVProctor(unittest.TestCase):
    def test_clean_frame_produces_no_violations(self):
        res = evaluate_cv_telemetry({
            "face_count": 1,
            "mean_brightness": 125.0,
            "center_offset_x": 0.05,
            "motion_score": 0.04,
        })
        self.assertEqual(len(res["detected_events"]), 0)

    def test_multiple_faces_and_occlusion(self):
        multi = evaluate_cv_telemetry({
            "face_count": 2,
            "mean_brightness": 120.0,
            "center_offset_x": 0.1,
            "motion_score": 0.05,
        })
        self.assertEqual(multi["detected_events"][0]["event_type"], "MULTIPLE_FACES")
        self.assertEqual(multi["detected_events"][0]["severity"], "HIGH")

        dark = evaluate_cv_telemetry({
            "face_count": 0,
            "mean_brightness": 10.0,
            "center_offset_x": 0.0,
            "motion_score": 0.01,
        })
        self.assertEqual(dark["detected_events"][0]["event_type"], "CAMERA_OCCLUDED")

    def test_looking_away_and_motion(self):
        res = evaluate_cv_telemetry({
            "face_count": 1,
            "mean_brightness": 115.0,
            "center_offset_x": 0.34,
            "motion_score": 0.41,
        })
        types = {e["event_type"] for e in res["detected_events"]}
        self.assertIn("LOOKING_AWAY", types)
        self.assertIn("SUSPICIOUS_MOTION", types)

    def test_integrity_score_and_risk_levels(self):
        clear = compute_integrity_summary([{"event_type": "EXAM_STARTED", "severity": "LOW"}])
        self.assertEqual(clear["integrity_score"], 100.0)
        self.assertEqual(clear["risk_level"], "CLEAR")

        flagged = compute_integrity_summary(
            [
                {"event_type": "MULTIPLE_FACES", "severity": "HIGH"},
                {"event_type": "TAB_SWITCH", "severity": "HIGH"},
                {"event_type": "COPY_PASTE_ATTEMPT", "severity": "HIGH"},
                {"event_type": "NO_FACE", "severity": "MEDIUM"},
            ],
            strictness="MEDIUM",
        )
        self.assertLess(flagged["integrity_score"], 70.0)
        self.assertEqual(flagged["risk_level"], "FLAGGED")


if __name__ == "__main__":
    unittest.main()
