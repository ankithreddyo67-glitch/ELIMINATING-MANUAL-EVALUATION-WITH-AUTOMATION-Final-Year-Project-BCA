"""Flask entry point for AutoExam AI."""

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, Response, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge

from backend.config import FRONTEND_DIR
from backend.cv_proctor import load_device_detector
from backend.database import init_db
from backend.exam_service import ServiceError
from backend.router import ExamRoutes


class FlaskExamRoutes(ExamRoutes):
    def __init__(self, db_path: Path | None) -> None:
        self.db_path = db_path

    @property
    def headers(self):
        return request.headers

    def _read_json_body(self) -> dict:
        try:
            raw = request.get_data(cache=False)
        except RequestEntityTooLarge:
            raise ServiceError("Payload too large.", 413) from None
        if not raw:
            return {}
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise ServiceError("Invalid JSON body.") from None
        if not isinstance(body, dict):
            raise ServiceError("JSON body must be an object.")
        return body

    @staticmethod
    def _send_json(status: int, data: dict) -> Response:
        return Response(
            json.dumps(data), status=status, content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )

    @staticmethod
    def _send_text(
        status: int, text: str, content_type: str = "text/plain; charset=utf-8",
        extra_headers: dict | None = None,
    ) -> Response:
        return Response(text, status=status, content_type=content_type, headers=extra_headers)

    def api(self, endpoint: str) -> Response:
        path = f"/api/{endpoint}"
        if request.method in {"GET", "HEAD"}:
            return self._handle_api_get(path, request.args.to_dict(flat=False))
        if request.method == "OPTIONS":
            return Response(status=204, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type",
            })
        return self._handle_api_write(request.method, path)

    def snapshot(self, filename: str) -> Response:
        try:
            path = self._snapshot_target(filename)
        except ServiceError as error:
            return self._send_json(error.status_code, {"error": error.message})
        response = send_file(path, conditional=False, etag=False)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


def create_app(db_path: Path | None = None) -> Flask:
    """Configure Flask routes and prepare the SQLite database."""
    init_db(db_path, seed=True)
    load_device_detector()
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 5_000_000
    routes = FlaskExamRoutes(db_path)

    app.add_url_rule("/api/<path:endpoint>", view_func=routes.api,
                     methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"])
    app.add_url_rule("/proctor_snapshots/<filename>", view_func=routes.snapshot)
    frontend_root = FRONTEND_DIR.resolve()

    @app.get("/")
    @app.get("/<path:asset>")
    def frontend(asset: str = "index.html") -> Response:
        path = (frontend_root / asset).resolve()
        if not path.is_relative_to(frontend_root) or not path.is_file():
            path = frontend_root / "index.html"
        if not path.is_file():
            return routes._send_text(404, "Frontend assets not found.")
        mime = {".js": "application/javascript", ".css": "text/css", ".html": "text/html"}
        return send_file(path, mimetype=mime.get(path.suffix))

    return app
