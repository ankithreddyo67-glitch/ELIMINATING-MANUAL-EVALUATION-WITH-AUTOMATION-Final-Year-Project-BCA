# AutoExam JavaScript

This package contains 34 browser JavaScript modules plus the HTML, CSS, and Python server needed to run AutoExam locally. The package includes student exam screens and results, faculty grading and question-bank tools, admin screens, analytics, and browser exam monitoring.

## Run locally

1. Extract the ZIP and open a terminal in the extracted folder.
2. Run `python app.py` with Python 3.10 or later.
3. Open http://127.0.0.1:8000. The terminal shows the local demo account credentials.

The server initializes a fresh SQLite database. For the optional Flask server, run `python -m pip install -r requirements.txt` first. The frontend uses native browser modules and does not need npm dependencies or a build step. Camera access requires browser permission.

## Main files

- `frontend/js/app.js` starts the application and switches between portals.
- `frontend/js/api.js` exposes shared session, theme, HTTP, and display helpers.
- `frontend/js/views-student.js`, `views-faculty.js`, and `views-admin.js` route each portal to its screens.
- `frontend/js/question-bank.js` provides question-bank actions and exam editing dialogs.
- `frontend/js/cv-proctor.js` handles browser monitoring during exams.
