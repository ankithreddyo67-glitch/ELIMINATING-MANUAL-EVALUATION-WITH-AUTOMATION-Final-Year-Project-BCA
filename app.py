"""Main entry point for the AI-Powered Automated Examination & Evaluation System."""

from __future__ import annotations

from http.server import ThreadingHTTPServer
from importlib.util import find_spec

from backend.config import HOST, PORT
from backend.cv_proctor import load_device_detector
from backend.database import init_db
from backend.router import ExamAPIHandler


def create_server(host: str = HOST, port: int = PORT) -> ThreadingHTTPServer:
    """Initialize database and instantiate the threaded HTTP server."""
    init_db(seed=True)
    load_device_detector()
    return ThreadingHTTPServer((host, port), ExamAPIHandler)


def main() -> None:
    print(f"AutoExam AI server running at http://{HOST}:{PORT}")
    print("Demo accounts:")
    print("  Admin   : admin@examai.edu   / Admin@123")
    print("  Faculty : faculty@examai.edu / Faculty@123")
    print("  Student : student1@examai.edu / Student@123")
    if find_spec("flask") is not None:
        from backend.flask_app import create_app

        create_app().run(host=HOST, port=PORT, debug=False)
        return

    print("Flask is unavailable. Starting the standard-library demo server.")
    print("Install Flask with: python -m pip install -r requirements.txt")
    server = create_server(HOST, PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down AutoExam AI server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
