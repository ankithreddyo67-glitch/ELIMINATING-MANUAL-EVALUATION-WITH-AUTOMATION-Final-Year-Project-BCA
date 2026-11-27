"""End-to-end REST API integration tests using an isolated temporary SQLite DB."""

import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from importlib.util import find_spec
from pathlib import Path

from backend.database import init_db
from backend.router import ExamAPIHandler


class _InMemorySocket:
    """Minimal socket adapter for testing BaseHTTPRequestHandler in-process."""

    def __init__(self, raw_request: bytes) -> None:
        self._rfile = io.BytesIO(raw_request)
        self._wfile = io.BytesIO()

    def makefile(self, mode: str, *args, **kwargs):  # type: ignore
        return self._rfile if "r" in mode else self._wfile

    def sendall(self, data: bytes) -> None:
        self._wfile.write(data)

    def close(self) -> None:
        pass


def dispatch_http(
    handler_cls,
    path: str,
    method: str = "GET",
    body: dict | None = None,
    token: str = "",
) -> tuple[int, dict | str]:
    if hasattr(handler_cls, "open"):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = handler_cls.open(path, method=method, json=body, headers=headers)
        with closing(response):
            content = response.get_json() if response.is_json else response.get_data(as_text=True)
            return response.status_code, content

    payload = json.dumps(body).encode("utf-8") if body is not None else b""
    headers = [f"{method} {path} HTTP/1.1", "Host: localhost"]
    if token:
        headers.append(f"Authorization: Bearer {token}")
    if body is not None:
        headers.append("Content-Type: application/json")
        headers.append(f"Content-Length: {len(payload)}")
    raw_req = ("\r\n".join(headers) + "\r\n\r\n").encode("ascii") + payload

    sock = _InMemorySocket(raw_req)
    # BaseHTTPRequestHandler runs handle() in __init__
    handler_cls(sock, ("127.0.0.1", 0), None)  # type: ignore

    raw_resp = sock._wfile.getvalue()
    head, _, body_bytes = raw_resp.partition(b"\r\n\r\n")
    status_line = head.decode("ascii", errors="replace").splitlines()[0]
    status_code = int(status_line.split()[1])
    text = body_bytes.decode("utf-8", errors="replace")
    if b"application/json" in head.lower():
        return status_code, json.loads(text) if text else {}
    return status_code, text


class TestExamAPIE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmpdir.name) / "test_exam.db"
        init_db(cls.db_path, seed=True)

        class TestHandler(ExamAPIHandler):
            db_path = cls.db_path

        cls.handler_cls = TestHandler

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmpdir.cleanup()

    def test_full_exam_evaluation_lifecycle(self) -> None:
        # 1. Health check & static index serving
        status, health = dispatch_http(self.handler_cls, "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["status"], "ok")

        st_html, html_body = dispatch_http(self.handler_cls, "/")
        self.assertEqual(st_html, 200)
        self.assertIn("AutoExam AI", html_body)

        # 2. Login as Student, Faculty, Admin
        st, stu_login = dispatch_http(
            self.handler_cls,
            "/api/auth/login",
            method="POST",
            body={"email": "student1@examai.edu", "password": "Student@123"},
        )
        self.assertEqual(st, 200)
        stu_token = stu_login["token"]

        st, fac_login = dispatch_http(
            self.handler_cls,
            "/api/auth/login",
            method="POST",
            body={"email": "faculty@examai.edu", "password": "Faculty@123"},
        )
        self.assertEqual(st, 200)
        fac_token = fac_login["token"]

        st, adm_login = dispatch_http(
            self.handler_cls,
            "/api/auth/login",
            method="POST",
            body={"email": "admin@examai.edu", "password": "Admin@123"},
        )
        self.assertEqual(st, 200)
        adm_token = adm_login["token"]

        # 3. RBAC check: student cannot list users or access analytics
        st, _ = dispatch_http(self.handler_cls, "/api/users", token=stu_token)
        self.assertEqual(st, 403)
        st, _ = dispatch_http(self.handler_cls, "/api/analytics", token=stu_token)
        self.assertEqual(st, 403)

        # 4. Faculty creates a new exam
        st, created_res = dispatch_http(
            self.handler_cls,
            "/api/exams",
            method="POST",
            token=fac_token,
            body={
                "title": "NLP & Vision Integration Test Exam",
                "subject": "CS499",
                "description": "End-to-end automated assessment check.",
                "duration_minutes": 20,
                "passing_percentage": 40,
                "proctoring_strictness": "MEDIUM",
                "questions": [
                    {
                        "question_type": "MCQ",
                        "prompt": "Which similarity metric compares vector angles in TF-IDF space?",
                        "options": ["A. Euclidean", "B. Cosine Similarity", "C. Manhattan", "D. Hamming"],
                        "model_answer": "B",
                        "max_marks": 5,
                    },
                    {
                        "question_type": "SUBJECTIVE",
                        "prompt": "Explain why automated subjective evaluation improves academic grading.",
                        "model_answer": (
                            "Automated subjective evaluation uses NLP similarity and rubric concept matching "
                            "to grade answers consistently, eliminate manual fatigue, and generate fast transparent feedback."
                        ),
                        "keywords": ["NLP", "rubric", "consistent", "manual", "feedback"],
                        "max_marks": 10,
                    },
                ],
            },
        )
        self.assertEqual(st, 201)
        exam = created_res["exam"]
        exam_id = exam["id"]
        q1_id = exam["questions"][0]["id"]
        q2_id = exam["questions"][1]["id"]

        # 5. Student starts attempt (ensure model_answer is hidden!)
        st, started = dispatch_http(
            self.handler_cls,
            f"/api/exams/{exam_id}/start",
            method="POST",
            token=stu_token,
            body={},
        )
        self.assertEqual(st, 200)
        attempt_id = started["attempt"]["id"]
        self.assertNotIn("model_answer", started["exam"]["questions"][1])

        # 6. Student saves draft & logs a CV proctoring event
        st, draft_res = dispatch_http(
            self.handler_cls,
            f"/api/attempts/{attempt_id}/draft",
            method="POST",
            token=stu_token,
            body={"question_id": q1_id, "student_answer": "B"},
        )
        self.assertEqual(st, 200)
        self.assertTrue(draft_res["saved"])

        st, proc_res = dispatch_http(
            self.handler_cls,
            f"/api/attempts/{attempt_id}/proctor",
            method="POST",
            token=stu_token,
            body={
                "event_type": "CV_FRAME",
                "metrics": {
                    "face_count": 1,
                    "mean_brightness": 110.0,
                    "center_offset_x": 0.30,
                    "motion_score": 0.05,
                },
            },
        )
        self.assertEqual(st, 200)
        self.assertEqual(proc_res["logged_count"], 1)
        self.assertLess(proc_res["integrity"]["integrity_score"], 100.0)

        st, tab_event = dispatch_http(
            self.handler_cls,
            f"/api/attempts/{attempt_id}/proctor",
            method="POST",
            token=stu_token,
            body={"event_type": "TAB_SWITCH", "details": "Exam tab became hidden."},
        )
        self.assertEqual(st, 200)
        self.assertEqual(tab_event["logged_events"][0]["event_type"], "TAB_SWITCH")
        self.assertEqual(tab_event["integrity"]["warning_count"], 1)
        self.assertEqual(dispatch_http(self.handler_cls, "/proctor_snapshots/example.jpg")[0], 401)
        self.assertEqual(
            dispatch_http(self.handler_cls, "/proctor_snapshots/example.jpg", token=stu_token)[0], 403
        )

        # 7. Student submits exam -> AI auto-grades immediately
        st, sub_res = dispatch_http(
            self.handler_cls,
            f"/api/attempts/{attempt_id}/submit",
            method="POST",
            token=stu_token,
            body={
                "answers": {
                    str(q1_id): "B",
                    str(q2_id): (
                        "Automated evaluation applies NLP semantic similarity and rubric concept checks to "
                        "grade responses consistently without manual bias while providing instant feedback."
                    ),
                },
                "auto_publish": False,
            },
        )
        self.assertEqual(st, 200)
        att = sub_res["attempt"]
        self.assertEqual(att["objective_score"], 5.0)
        self.assertGreaterEqual(att["subjective_score"], 7.5)
        self.assertTrue(att["passed"])

        # 8. Faculty overrides marks & publishes result
        st, ov_res = dispatch_http(
            self.handler_cls,
            f"/api/attempts/{attempt_id}/override",
            method="POST",
            token=fac_token,
            body={
                "question_id": q2_id,
                "final_marks": 9.5,
                "faculty_comment": "Clear explanation of NLP rubric alignment.",
            },
        )
        self.assertEqual(st, 200)
        self.assertEqual(ov_res["attempt"]["total_score"], 14.5)

        st, pub_res = dispatch_http(
            self.handler_cls,
            f"/api/attempts/{attempt_id}/publish",
            method="POST",
            token=fac_token,
            body={"faculty_remarks": "Verified and published."},
        )
        self.assertEqual(st, 200)
        self.assertEqual(pub_res["attempt"]["status"], "PUBLISHED")

        # 9. Faculty NLP live preview & CSV export
        st, nlp_res = dispatch_http(
            self.handler_cls,
            "/api/nlp/preview",
            method="POST",
            token=fac_token,
            body={
                "question_type": "SUBJECTIVE",
                "model_answer": "TF-IDF weights rare terms higher than common terms.",
                "keywords": ["TF-IDF", "rare terms"],
                "student_answer": "TF-IDF assigns higher weights to rare terms across documents.",
                "max_marks": 5,
            },
        )
        self.assertEqual(st, 200)
        self.assertGreaterEqual(nlp_res["evaluation"]["awarded_marks"], 3.5)

        st_csv, csv_body = dispatch_http(
            self.handler_cls,
            f"/api/exams/{exam_id}/export",
            token=fac_token,
        )
        self.assertEqual(st_csv, 200)
        self.assertIn("Enrollment No,Student Name", csv_body)

        # Simulate an expired attempt to verify that resuming cannot reset the clock.
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                """UPDATE exam_attempts
                   SET status = 'IN_PROGRESS', started_at = datetime('now', '-21 minutes')
                   WHERE id = ?""",
                (attempt_id,),
            )
        st, resumed = dispatch_http(
            self.handler_cls, f"/api/exams/{exam_id}/start", method="POST", token=stu_token, body={}
        )
        self.assertEqual(st, 200)
        self.assertEqual(resumed["remaining_seconds"], 0)
        st, _ = dispatch_http(
            self.handler_cls,
            f"/api/attempts/{attempt_id}/draft",
            method="POST",
            token=stu_token,
            body={"question_id": q1_id, "student_answer": "A"},
        )
        self.assertEqual(st, 409)
        st, expired_result = dispatch_http(
            self.handler_cls,
            f"/api/attempts/{attempt_id}/submit",
            method="POST",
            token=stu_token,
            body={"answers": {str(q1_id): "A"}},
        )
        self.assertEqual(st, 200)
        self.assertEqual(expired_result["answers"][0]["student_answer"], "B")

        self.assertIn("Aarav Sharma", csv_body)

        # 10. Admin audit logs & analytics
        st, logs_res = dispatch_http(self.handler_cls, "/api/audit-logs", token=adm_token)
        self.assertEqual(st, 200)
        self.assertGreaterEqual(len(logs_res["logs"]), 3)


    def test_admin_accounts_subjects_and_exam_assignments(self):
        def call(path, method="GET", token="", body=None):
            return dispatch_http(self.handler_cls, path, method=method, token=token, body=body)

        def sign_in(email, password):
            status, result = call("/api/auth/login", "POST", body={"email": email, "password": password})
            self.assertEqual(status, 200)
            return result["token"]

        admin = sign_in("admin@examai.edu", "Admin@123")
        faculty = sign_in("faculty@examai.edu", "Faculty@123")
        student = sign_in("student1@examai.edu", "Student@123")
        status, account = call("/api/users", "POST", admin, {
            "full_name": "Assignment Candidate", "email": "candidate@example.org", "password": "Sample123"
        })
        self.assertEqual(status, 201, account)
        candidate = sign_in("candidate@example.org", "Sample123")
        user_path = f"/api/users/{account['user']['id']}"
        self.assertEqual(call(user_path, "PATCH", admin, {"is_active": False})[0], 200)
        self.assertEqual(call("/api/auth/me", token=candidate)[0], 403)
        self.assertEqual(call(user_path, "DELETE", admin)[0], 200)
        self.assertEqual(call("/api/subjects", token=faculty)[0], 403)
        status, subject = call("/api/subjects", "POST", admin, {"name": "Programming", "code": "CS200"})
        self.assertEqual(status, 201, subject)
        self.assertEqual(call(f"/api/subjects/{subject['id']}", "DELETE", admin)[0], 200)

        status, result = call("/api/exams", "POST", faculty, {
            "title": "Assigned exam", "subject": "Programming",
            "questions": [{"question_type": "TRUE_FALSE", "prompt": "Python is case sensitive.",
                           "model_answer": "True"}],
        })
        self.assertEqual(status, 201, result)
        exam_id = result["exam"]["id"]
        exam = f"/api/exams/{exam_id}"
        student_id = call("/api/auth/me", token=student)[1]["user"]["id"]
        self.assertEqual(call(exam + "/assignments", "PATCH", admin, {"student_ids": []})[0], 200)
        self.assertEqual(call(exam + "/start", "POST", student)[0], 403)
        self.assertNotIn(exam_id, [row["id"] for row in call("/api/exams", token=student)[1]["exams"]])
        self.assertEqual(call(exam + "/assignments", "PATCH", admin, {"student_ids": [student_id]})[0], 200)
        self.assertEqual(call(exam + "/start", "POST", student)[0], 200)
        self.assertEqual(call(exam, "DELETE", faculty)[0], 409)

    def test_question_bank_paper_and_schedule(self) -> None:
        def call(path, method="GET", token="", body=None):
            return dispatch_http(self.handler_cls, path, method=method, token=token, body=body)

        def login(role, password):
            status, result = call("/api/auth/login", "POST", body={
                "email": f"{role}@examai.edu", "password": password,
            })
            self.assertEqual(status, 200)
            return result["token"]

        faculty = login("faculty", "Faculty@123")
        student = login("student1", "Student@123")
        admin = login("admin", "Admin@123")
        self.assertEqual(call("/api/question-bank", token=student)[0], 403)
        definitions = [
            {
                "question_type": "TRUE_FALSE", "prompt": "Python strings are immutable.",
                "model_answer": "True", "max_marks": 2,
            },
            {
                "question_type": "PROGRAMMING", "prompt": "Write a function returning two.",
                "model_answer": "def answer():\n    return 2", "max_marks": 5,
            },
        ]
        ids = []
        for question in definitions:
            question.update(subject="Python Basics", difficulty="HARD")
            status, result = call("/api/question-bank", "POST", faculty, question)
            self.assertEqual(status, 201, result)
            ids.append(result["id"])
        self.assertEqual(call(f"/api/question-bank/{ids[0]}", "DELETE", admin)[0], 404)

        payload = {
            "title": "Scheduled Python Exam",
            "subject": "Python Basics",
            "status": "DRAFT",
            "duration_minutes": 20,
            "opens_at": "2099-11-27T09:00:00+05:30",
            "closes_at": "2099-11-27T10:00:00+05:30",
            "random_selection": {"count": 2, "subject": "python basics", "difficulty": "HARD"},
        }
        status, result = call("/api/exams", "POST", faculty, payload)
        self.assertEqual(status, 201, result)
        exam = result["exam"]
        paper_path = f"/api/exams/{exam['id']}"
        self.assertEqual(exam["opens_at"], "2099-11-27T03:30:00+00:00")
        self.assertEqual({q["question_type"] for q in exam["questions"]}, {"TRUE_FALSE", "PROGRAMMING"})
        self.assertEqual(call(paper_path, token=student)[0], 403)

        self.assertEqual(call(f"/api/question-bank/{ids[0]}", "PATCH", faculty, {
            **definitions[0], "prompt": "Edited bank prompt",
        })[0], 200)
        self.assertEqual(call(f"/api/question-bank/{ids[1]}", "DELETE", faculty)[0], 200)
        status, result = call(paper_path, token=faculty)
        self.assertEqual(status, 200)
        self.assertEqual(result["exam"]["questions"], exam["questions"])

        status, edited = call(paper_path + "/paper", "PATCH", faculty, {
            "questions": list(reversed(exam["questions"])),
        })
        self.assertEqual(status, 200, edited)
        self.assertEqual(
            [q["question_type"] for q in edited["exam"]["questions"]],
            [q["question_type"] for q in reversed(exam["questions"])],
        )
        self.assertEqual(call(paper_path + "/status", "PATCH", faculty, {"status": "PUBLISHED"})[0], 200)
        self.assertEqual(call(paper_path + "/start", "POST", student, {})[0], 409)
        self.assertEqual(call(paper_path + "/paper", "PATCH", faculty, {"questions": definitions})[0], 409)
        self.assertEqual(call(paper_path + "/schedule", "PATCH", faculty, {
            "opens_at": "2020-01-01T00:00:00Z", "closes_at": "2020-01-02T00:00:00Z",
        })[0], 200)
        self.assertEqual(call(paper_path + "/start", "POST", student, {})[0], 409)
        self.assertEqual(call(paper_path + "/schedule", "PATCH", faculty, {})[0], 200)
        status, started = call(paper_path + "/start", "POST", student, {})
        self.assertEqual(status, 200, started)
        questions = {q["question_type"]: q for q in started["exam"]["questions"]}
        self.assertEqual(questions["TRUE_FALSE"]["options"], ["True", "False"])
        self.assertNotIn("model_answer", questions["PROGRAMMING"])
        status, graded = call(f"/api/attempts/{started['attempt']['id']}/submit", "POST", student, {
            "answers": {
                str(questions["TRUE_FALSE"]["id"]): "TRUE",
                str(questions["PROGRAMMING"]["id"]): "def answer():\n    return 1 + 1",
            },
        })
        self.assertEqual(status, 200, graded)
        self.assertEqual(graded["attempt"]["objective_score"], 2)
        code_answer = next(q for q in graded["answers"] if q["question_type"] == "PROGRAMMING")
        self.assertTrue(code_answer["needs_review"])
        self.assertEqual(code_answer["ai_marks"], 0)


@unittest.skipUnless(find_spec("flask"), "Flask dependency is unavailable.")
class TestFlaskExamAPIE2E(TestExamAPIE2E):
    @classmethod
    def setUpClass(cls) -> None:
        from backend.flask_app import create_app

        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmpdir.name) / "test_flask_exam.db"
        app = create_app(cls.db_path)
        app.config["TESTING"] = True
        cls.handler_cls = app.test_client()

    def test_flask_request_validation_and_assets(self) -> None:
        client = self.handler_cls
        with closing(client.get("/js/app.js")) as script:
            self.assertEqual(script.status_code, 200)
            self.assertEqual(script.mimetype, "application/javascript")
        self.assertEqual(client.options("/api/exams").status_code, 204)
        self.assertEqual(client.post("/api/auth/login", data=b"{").status_code, 400)
        self.assertEqual(client.post("/api/auth/login", data=b"x" * 5_000_001).status_code, 413)


if __name__ == "__main__":
    unittest.main()
