# AutoExam AI Website Server

**Eliminating Manual Evaluation with Automation**

AutoExam is a local examination website with student, faculty, and admin portals. Faculty can build and publish exams, review automated grades, and inspect proctoring events. Students can submit answers and view results when faculty publish them.

## Start the website

1. Extract the ZIP and open a terminal in the extracted folder.
2. Run `python app.py` with Python 3.10 or later. On Windows, you can also use `run.bat`.
3. Open [http://127.0.0.1:8000](http://127.0.0.1:8000).
4. Use the demo accounts printed in the terminal to try the student, faculty, and admin portals.

The first run creates and seeds `data/exam_system.db` with demo data. Stop the server with Ctrl+C.

## Server options

- The default launcher works with Python's standard library. Run `python -m pip install -r requirements.txt` to install Flask. The launcher uses Flask when it is available.
- To add the optional OpenCV dependencies, run `python -m pip install -r requirements-vision.txt`. Browser camera access requires permission.
- Use the `EXAM_PORT` environment variable if port 8000 is busy. For PowerShell, run `$env:EXAM_PORT = '8080'` before starting the app, then open http://127.0.0.1:8080.
- Use `EXAM_DB_PATH` to set a different SQLite database path.
- The seeded accounts and built-in signing configuration are for local demos. Keep this package on localhost.

## Project layout

| Path | Purpose |
| --- | --- |
| `app.py` | Server launcher and demo credentials |
| `backend/` | HTTP routes, authentication, database, grading, and proctoring |
| `frontend/index.html` | Browser entry page |
| `frontend/js/` | Portal, exam, and API logic |
| `frontend/css/` | Main stylesheet and 10 component stylesheets |
| `tests/` | API, grading, and proctoring tests |
| `run.bat`, `start.ps1` | Windows launch scripts |

Run the included tests from this folder with `python -m unittest discover -s tests -v`.
