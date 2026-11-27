# AutoExam HTML and CSS

The project contains one HTML entry page and 33 CSS files, including the main stylesheet and 32 component stylesheets. The JavaScript frontend renders the student, faculty, and admin screens inside that HTML page.

## Start locally

1. Extract the archive and open a terminal in the extracted folder.
2. Run `python app.py` with Python 3.10 or later.
3. Open http://127.0.0.1:8000 and use the demo credentials printed in the terminal.

The bundled Python server creates a fresh local SQLite database. The frontend requires no JavaScript build step.

## Find the page and styles

- `frontend/index.html` loads the stylesheet and JavaScript entry point.
- `frontend/css/styles.css` loads the component stylesheets in cascade order.
- The numbered CSS files contain the themes, app shell, authentication, exam room, proctoring, reports, and assessment dialogs.
- `frontend/js/` contains the scripts that render the screens and connect to the exam API.
