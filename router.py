"""HTTP REST API router and static file server."""

from __future__ import annotations

import json
import logging
import mimetypes
import re
from contextlib import closing
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from backend import exam_service
from backend.auth import verify_token
from backend.config import FRONTEND_DIR, UPLOAD_DIR
from backend.cv_proctor import HAS_OPENCV
from backend.database import get_connection
from backend.nlp_evaluator import evaluate_answer


class ExamRoutes:
    """Shared endpoint dispatch for Flask and the standard-library launcher."""

    db_path: Path | None = None

    def _require_auth(self, roles: tuple[str, ...] | None = None) -> dict[str, Any]:
        auth_header = self.headers.get("Authorization") or ""
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        claims = verify_token(token)
        if not claims:
            raise exam_service.ServiceError("Authentication required.", status_code=401)
        with closing(get_connection(self.db_path)) as auth_db:
            account = auth_db.execute("SELECT role, is_active FROM users WHERE id = ?", (claims["uid"],)).fetchone()
        if not account or not account["is_active"]:
            raise exam_service.ServiceError("Account is unavailable.", 403)
        claims["role"] = account["role"]
        if roles and claims.get("role") not in roles:
            raise exam_service.ServiceError("Insufficient permissions for this action.", status_code=403)
        return claims

    def _snapshot_target(self, filename: str) -> Path:
        self._require_auth(("FACULTY", "ADMIN"))
        directory = UPLOAD_DIR.resolve()
        target = (directory / filename).resolve()
        if target.parent != directory or not target.is_file():
            raise exam_service.ServiceError("Snapshot not found.", 404)
        return target

    def _handle_api_get(self, path: str, query: dict[str, list[str]]):
        conn = get_connection(self.db_path)
        try:
            if path == "/api/health":
                return self._send_json(200, {
                    "status": "ok",
                    "opencv_enabled": HAS_OPENCV,
                    "nlp_engine": "TF-IDF + BM25 + Bigram + Rubric Concept Ensemble",
                })

            if path == "/api/auth/me":
                user = self._require_auth()
                row = conn.execute(
                    "SELECT id, full_name, email, role, department, enrollment_no, is_active, created_at FROM users WHERE id = ?",
                    (user["uid"],),
                ).fetchone()
                if not row:
                    raise exam_service.ServiceError("User not found.", status_code=404)
                return self._send_json(200, {"user": dict(row)})

            if path == "/api/subjects":
                self._require_auth(("ADMIN",))
                return self._send_json(200, {"subjects": exam_service.list_subjects(conn)})

            assignment = re.fullmatch(r"/api/exams/(\d+)/assignments", path)
            if assignment:
                self._require_auth(("ADMIN",))
                return self._send_json(200, exam_service.exam_assignments(conn, int(assignment[1])))

            if path == "/api/users":
                self._require_auth(("ADMIN",))
                return self._send_json(200, {"users": exam_service.list_users(conn)})

            if path == "/api/question-bank":
                user = self._require_auth(("FACULTY", "ADMIN"))
                questions = exam_service.list_bank_questions(conn, user["uid"])
                return self._send_json(200, {"questions": questions})

            if path == "/api/exams":
                user = self._require_auth()
                return self._send_json(200, {"exams": exam_service.list_exams(conn, user)})

            m = re.fullmatch(r"/api/exams/(\d+)", path)
            if m:
                user = self._require_auth()
                exam_id = int(m.group(1))
                include_ans = user["role"] in ("FACULTY", "ADMIN")
                if not include_ans:
                    active = conn.execute(
                        """SELECT 1 FROM exam_attempts
                           WHERE exam_id = ? AND student_id = ? AND status = 'IN_PROGRESS'""",
                        (exam_id, user["uid"]),
                    ).fetchone()
                    if not active:
                        raise exam_service.ServiceError("Start the examination to view the paper.", 403)
                return self._send_json(200, {"exam": exam_service.get_exam_detail(conn, exam_id, include_answers=include_ans)})

            m = re.fullmatch(r"/api/exams/(\d+)/export", path)
            if m:
                self._require_auth(("FACULTY", "ADMIN"))
                exam_id = int(m.group(1))
                csv_text = exam_service.export_exam_csv(conn, exam_id)
                return self._send_text(
                    200,
                    csv_text,
                    content_type="text/csv; charset=utf-8",
                    extra_headers={"Content-Disposition": f'attachment; filename="exam_{exam_id}_results.csv"'},
                )

            if path == "/api/attempts":
                user = self._require_auth()
                exam_id = int(query["exam_id"][0]) if "exam_id" in query else None
                return self._send_json(200, {"attempts": exam_service.list_attempts(conn, user, exam_id=exam_id)})

            m = re.fullmatch(r"/api/attempts/(\d+)", path)
            if m:
                user = self._require_auth()
                attempt_id = int(m.group(1))
                detail = exam_service.get_attempt_detail(conn, attempt_id, include_model_answers=True)
                if user["role"] == "STUDENT" and detail["attempt"]["student_id"] != user["uid"]:
                    raise exam_service.ServiceError("Access denied.", status_code=403)
                if user["role"] == "STUDENT" and detail["attempt"]["status"] == "IN_PROGRESS":
                    for ans in detail["answers"]:
                        ans.pop("model_answer", None)
                        ans.pop("keywords", None)
                return self._send_json(200, detail)

            if path == "/api/analytics":
                self._require_auth(("FACULTY", "ADMIN"))
                exam_id = int(query["exam_id"][0]) if "exam_id" in query and query["exam_id"][0] else None
                return self._send_json(200, exam_service.get_system_analytics(conn, exam_id=exam_id))

            if path == "/api/audit-logs":
                self._require_auth(("ADMIN",))
                return self._send_json(200, {"logs": exam_service.list_audit_logs(conn)})

            raise exam_service.ServiceError("API endpoint not found.", status_code=404)
        except exam_service.ServiceError as err:
            return self._send_json(err.status_code, {"error": err.message})
        except Exception:
            logging.exception("Exam API request failed")
            return self._send_json(500, {"error": "Internal server error."})
        finally:
            conn.close()

    def _handle_api_write(self, method: str, path: str):
        conn = get_connection(self.db_path)
        try:
            body = self._read_json_body()

            if method == "POST" and path == "/api/auth/register":
                res = exam_service.register_user(conn, body)
                return self._send_json(201, res)

            if method == "POST" and path == "/api/auth/login":
                res = exam_service.authenticate_user(conn, body.get("email", ""), body.get("password", ""))
                return self._send_json(200, res)

            if method == "POST" and path == "/api/question-bank":
                user = self._require_auth(("FACULTY", "ADMIN"))
                question_id = exam_service.save_bank_question(conn, user["uid"], body)
                return self._send_json(201, {"id": question_id})

            m = re.fullmatch(r"/api/question-bank/(\d+)", path)
            if m and method in ("PATCH", "DELETE"):
                user = self._require_auth(("FACULTY", "ADMIN"))
                question_id = int(m.group(1))
                if method == "PATCH":
                    exam_service.save_bank_question(conn, user["uid"], body, question_id)
                else:
                    exam_service.delete_bank_question(conn, user["uid"], question_id)
                return self._send_json(200, {"id": question_id})

            if path == "/api/users" and method == "POST":
                user = self._require_auth(("ADMIN",))
                result = exam_service.register_user(conn, body, admin_id=user["uid"])
                return self._send_json(201, {"user": result["user"]})

            m = re.fullmatch(r"/api/users/(\d+)", path)
            if m and method == "DELETE":
                user = self._require_auth(("ADMIN",))
                exam_service.delete_user(conn, user["uid"], int(m[1]))
                return self._send_json(200, {"deleted": True})

            m = re.fullmatch(r"/api/exams/(\d+)", path)
            if m and method == "DELETE":
                user = self._require_auth(("FACULTY", "ADMIN"))
                exam_service.delete_exam(conn, user, int(m[1]))
                return self._send_json(200, {"deleted": True})

            m = re.fullmatch(r"/api/subjects(?:/(\d+))?", path)
            if m and ((method == "POST" and m[1] is None) or (method in ("PATCH", "DELETE") and m[1])):
                user = self._require_auth(("ADMIN",))
                subject_id = int(m[1]) if m[1] else None
                result = exam_service.change_subject(conn, user["uid"], body, subject_id, method == "DELETE")
                return self._send_json(201 if method == "POST" else 200, {"id": result})

            m = re.fullmatch(r"/api/exams/(\d+)/assignments", path)
            if m and method == "PATCH":
                user = self._require_auth(("ADMIN",))
                result = exam_service.set_exam_assignments(conn, user["uid"], int(m[1]), body)
                return self._send_json(200, result)

            m = re.fullmatch(r"/api/exams/(\d+)/paper", path)
            if m and method == "PATCH":
                user = self._require_auth(("FACULTY", "ADMIN"))
                exam = exam_service.update_draft_paper(conn, user, int(m.group(1)), body)
                return self._send_json(200, {"exam": exam})

            m = re.fullmatch(r"/api/exams/(\d+)/schedule", path)
            if m and method == "PATCH":
                user = self._require_auth(("FACULTY", "ADMIN"))
                exam = exam_service.update_exam_schedule(conn, user, int(m.group(1)), body)
                return self._send_json(200, {"exam": exam})

            if method == "PATCH":
                m = re.fullmatch(r"/api/users/(\d+)", path)
                if m:
                    user = self._require_auth(("ADMIN",))
                    updated = exam_service.update_user_status_or_role(conn, user["uid"], int(m.group(1)), body)
                    return self._send_json(200, {"user": updated})

                m = re.fullmatch(r"/api/exams/(\d+)/status", path)
                if m:
                    user = self._require_auth(("FACULTY", "ADMIN"))
                    updated = exam_service.update_exam_status(conn, user["uid"], int(m.group(1)), body.get("status", ""))
                    return self._send_json(200, {"exam": updated})

            if method == "POST" and path == "/api/exams":
                user = self._require_auth(("FACULTY", "ADMIN"))
                created = exam_service.create_exam(conn, user["uid"], body)
                return self._send_json(201, {"exam": created})

            if method == "POST":
                m = re.fullmatch(r"/api/exams/(\d+)/start", path)
                if m:
                    user = self._require_auth(("STUDENT",))
                    started = exam_service.start_attempt(conn, int(m.group(1)), user["uid"])
                    return self._send_json(200, started)

                m = re.fullmatch(r"/api/attempts/(\d+)/draft", path)
                if m:
                    user = self._require_auth(("STUDENT",))
                    res = exam_service.save_draft_answer(
                        conn,
                        int(m.group(1)),
                        user["uid"],
                        int(body.get("question_id")),
                        str(body.get("student_answer") or ""),
                    )
                    return self._send_json(200, res)

                m = re.fullmatch(r"/api/attempts/(\d+)/submit", path)
                if m:
                    user = self._require_auth(("STUDENT",))
                    res = exam_service.submit_and_evaluate_attempt(
                        conn,
                        int(m.group(1)),
                        user["uid"],
                        body.get("answers") or {},
                        auto_publish=bool(body.get("auto_publish", True)),
                    )
                    return self._send_json(200, res)

                m = re.fullmatch(r"/api/attempts/(\d+)/proctor", path)
                if m:
                    user = self._require_auth(("STUDENT",))
                    res = exam_service.record_proctor_telemetry(conn, int(m.group(1)), user["uid"], body)
                    return self._send_json(200, res)

                m = re.fullmatch(r"/api/attempts/(\d+)/evaluate", path)
                if m:
                    self._require_auth(("FACULTY", "ADMIN"))
                    res = exam_service.run_ai_evaluation_for_attempt(conn, int(m.group(1)))
                    return self._send_json(200, res)

                m = re.fullmatch(r"/api/attempts/(\d+)/override", path)
                if m:
                    user = self._require_auth(("FACULTY", "ADMIN"))
                    res = exam_service.override_answer_marks(
                        conn,
                        user["uid"],
                        int(m.group(1)),
                        int(body.get("question_id")),
                        float(body.get("final_marks")),
                        str(body.get("faculty_comment") or ""),
                    )
                    return self._send_json(200, res)

                m = re.fullmatch(r"/api/attempts/(\d+)/publish", path)
                if m:
                    user = self._require_auth(("FACULTY", "ADMIN"))
                    res = exam_service.publish_attempt_result(
                        conn,
                        user["uid"],
                        int(m.group(1)),
                        str(body.get("faculty_remarks") or ""),
                    )
                    return self._send_json(200, res)

                if path == "/api/nlp/preview":
                    self._require_auth(("FACULTY", "ADMIN"))
                    keywords = body.get("keywords") or []
                    if isinstance(keywords, str):
                        keywords = [k.strip() for k in keywords.split(",") if k.strip()]
                    res = evaluate_answer(
                        str(body.get("question_type") or "SUBJECTIVE"),
                        str(body.get("student_answer") or ""),
                        str(body.get("model_answer") or ""),
                        keywords,
                        float(body.get("max_marks") or 10.0),
                    )
                    return self._send_json(200, {"evaluation": res})

            raise exam_service.ServiceError("API endpoint not found.", status_code=404)
        except exam_service.ServiceError as err:
            return self._send_json(err.status_code, {"error": err.message})
        except Exception:
            logging.exception("Exam API request failed")
            return self._send_json(500, {"error": "Internal server error."})
        finally:
            conn.close()

class ExamAPIHandler(ExamRoutes, BaseHTTPRequestHandler):
    """Standard-library HTTP transport for dependency-free local demos."""

    server_version = "AutoExamAI/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        # Keep console output clean and concise
        return

    def _send_json(self, status: int, data: Any, extra_headers: dict[str, str] | None = None) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_text(
        self,
        status: int,
        text: str,
        content_type: str = "text/plain; charset=utf-8",
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        if length > 5_000_000:
            raise exam_service.ServiceError("Payload too large.", status_code=413)
        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise exam_service.ServiceError(f"Invalid JSON body: {exc}", status_code=400) from exc
        if not isinstance(parsed, dict):
            raise exam_service.ServiceError("JSON body must be an object.", status_code=400)
        return parsed

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path.startswith("/api/"):
            self._handle_api_get(path, query)
            return

        if path.startswith("/proctor_snapshots/"):
            self._serve_snapshot(path)
            return

        self._serve_static(path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        self._handle_api_write("POST", parsed.path)

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        self._handle_api_write("PATCH", parsed.path)

    def do_DELETE(self) -> None:
        self._handle_api_write("DELETE", urlparse(self.path).path)

    def _serve_snapshot(self, url_path: str) -> None:
        try:
            target = self._snapshot_target(Path(url_path).name)
        except exam_service.ServiceError as exc:
            self._send_json(exc.status_code, {"error": exc.message})
            return
        mime, _ = mimetypes.guess_type(str(target))
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime or "image/jpeg")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_static(self, url_path: str) -> None:
        clean = url_path.lstrip("/") or "index.html"
        target = (FRONTEND_DIR / clean).resolve()
        frontend_root = FRONTEND_DIR.resolve()
        if not target.is_relative_to(frontend_root) or not target.is_file():
            # SPA fallback to index.html
            target = frontend_root / "index.html"

        if not target.is_file():
            self._send_text(404, "Frontend assets not found.")
            return

        mime, _ = mimetypes.guess_type(str(target))
        if target.suffix == ".js":
            mime = "application/javascript; charset=utf-8"
        elif target.suffix == ".css":
            mime = "text/css; charset=utf-8"
        elif target.suffix == ".html":
            mime = "text/html; charset=utf-8"

        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
