# AutoExam AI — Automated Examination & Subjective Evaluation System

An end-to-end **AI-powered automated examination, NLP subjective grading, and Computer Vision proctoring platform** designed to eliminate manual grading bottlenecks, reduce evaluation inconsistency, automate marks calculation, and preserve academic integrity.

---

## Core Capabilities

### Faculty question management

1. Sign in as Faculty and open **Exams & Question Bank → Open question bank**. Add, edit, or delete questions, and filter by subject and difficulty. The five supported formats are multiple choice, true/false, short answer, descriptive, and programming.
2. Choose **Create exam** and either write questions, select entries from your bank, or generate a random paper by subject and difficulty. A generated paper uses unique questions copied when the exam is created. Later bank changes do not change it.
3. Save as a draft to review or edit its questions, including their order, before publishing. Set the start window in your browser's local time. The closing time stops new attempts. Students who have already started keep the attempt duration shown in the exam.
4. Review results using the faculty submissions screen. Multiple-choice and true/false questions use answer keys, and short/descriptive answers use the existing NLP grader. Programming questions compare source text with reference code. A different nonempty submission requires faculty review and initially receives zero marks. The application never runs submitted code.

### 1. Intelligent Subjective & Objective Evaluation (`backend/nlp_evaluator.py`)
- **MCQ & Short Answer Grading**: Exact option matching for objective items and fuzzy + concept-based evaluation for short factual answers.
- **Subjective Answer ML/NLP Ensemble**:
  - **Text Normalization & Synonym Canonicalization**: Stopword filtering, lightweight stemming, and academic/technical synonym alignment.
  - **TF-IDF Vectorizer + Cosine Similarity**: Corpus-aware term weighting across the model answer and peer submissions.
  - **BM25 Term Relevance & Bigram Phrase F1**: Captures multi-word technical concepts without over-penalizing paraphrasing.
  - **Rubric Key-Concept Coverage**: Tracks matched vs. missing faculty concepts (with auto-extracted fallback concepts).
  - **Negation Polarity Guard**: Flags polarity contradictions (e.g., `"does not reduce"` vs. `"reduces"`).
  - **Explainable Confidence & Faculty Review Flagging**: Outputs transparent breakdowns, constructive feedback, and flags low-confidence answers for human review.

### 2. Automated Computer Vision & Telemetry Proctoring (`frontend/js/cv-proctor.js`, `backend/cv_proctor.py`)
- **Live WebRTC + Canvas CV Engine**: Runs YCbCr skin-chrominance clustering, face-region counting (`NO_FACE`, `MULTIPLE_FACES`), centroid head-pose offset (`LOOKING_AWAY`), brightness/occlusion (`CAMERA_OCCLUDED`), and inter-frame motion energy (`SUSPICIOUS_MOTION`).
- **Optional OpenCV Server Verification**: Automatically upgrades snapshot inspection to `cv2` Haar-cascade face detection when `opencv-python` is installed.
- **Browser Academic Integrity Guards**: Shows a warning when the exam tab is hidden, blocks external links activated from the exam page, and logs tab visibility (`TAB_SWITCH`), window focus loss (`WINDOW_BLUR`), fullscreen exits (`FULLSCREEN_EXIT`), copy/paste attempts, and DevTools shortcuts.
- **Dynamic Integrity Score (0–100%)**: Real-time risk classification (`CLEAR`, `WATCH`, `FLAGGED`) with flagged JPEG snapshot evidence for faculty audit.

### 3. Role-Based Full-Stack Portals (`frontend/`, `backend/router.py`, `backend/exam_service.py`)
- **Student Portal**: Pre-exam webcam/environment readiness check, fullscreen proctored exam room with server-timed countdown and auto-saved drafts, instant AI-graded report cards, and printable PDF grade reports.
- **Faculty Portal**: Exam & rubric question-bank builder, submissions review & proctoring audit console, 1-click mark overrides with recalculation, **Live AI NLP Grader Sandbox**, analytics charts, and CSV grade-sheet exports.
- **Admin Portal**: User & RBAC management, system capability diagnostics, analytics overview, and immutable audit logs.

---

## Project Structure

```text
├── app.py                      # Main launcher for Flask and the offline demo
├── requirements.txt            # Flask dependency
├── run.bat                     # Windows batch launcher
├── start.ps1                   # PowerShell launcher
├── backend/
│   ├── config.py               # Configuration, penalties, thresholds
│   ├── auth.py                 # Password hashing (bcrypt/PBKDF2) & HMAC-SHA256 tokens
│   ├── database.py             # SQLite schema & realistic seeded demo dataset
│   ├── nlp_evaluator.py        # ML/NLP subjective & objective grading engine
│   ├── cv_proctor.py           # CV telemetry & integrity scoring engine
│   ├── exam_service.py         # Exam lifecycle, auto-grading, analytics, CSV export
│   └── router.py               # Shared REST API and offline demo server
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   └── js/
│       ├── api.js
│       ├── app.js
│       ├── charts.js
│       ├── cv-proctor.js
│       ├── views-auth.js
│       ├── views-student.js
│       ├── views-faculty.js
│       └── views-admin.js
└── tests/
    ├── test_nlp_evaluator.py
    ├── test_cv_proctor.py
    └── test_api_e2e.py
```

---

## Running the Project

### Flask launch

Use Python 3.10 or later. From the project folder, run:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). You can also start the Flask app directly with `python -m flask --app backend.flask_app:create_app run --port 8000`.

### Windows demo launcher
Double-click `run.bat` or run:
```powershell
.\start.ps1
```
Then open `http://127.0.0.1:8000` in your browser.

The Windows launcher uses Flask when installed and starts the standard-library demo server when Flask is unavailable.

### Pre-Seeded Demo Accounts
| Role | Email | Password |
|---|---|---|
| **Student** | `student1@examai.edu` | `Student@123` |
| **Faculty** | `faculty@examai.edu` | `Faculty@123` |
| **Admin** | `admin@examai.edu` | `Admin@123` |

One-click demo sign-in buttons are also available right on the login page.

---

## Running Automated Tests
```bash
python -m unittest discover -s tests -v
```


## Proctoring and exam deadlines

A hidden exam tab triggers an immediate warning and a faculty log entry when the server is reachable. External links activated from within the exam page are blocked and logged. An ordinary browser can report visibility and focus changes but cannot see which other websites or apps are open.

The server calculates remaining time from the original attempt start. After expiry, it rejects draft updates and evaluates the saved drafts on submission. Webcam alerts are review signals and can be affected by lighting, framing, and interruptions.

### Enable webcam device detection

Core exam and grading features run without computer-vision packages. To flag visible phones and laptops, install the optional dependencies in a compatible Python environment. Download the matching **MobileNet-SSD v2 (2018-03-29)** weights and text graph from the [OpenCV TensorFlow model table](https://github.com/opencv/opencv/wiki/TensorFlow-Object-Detection-API#use-existing-config-file-for-your-model). Extract the weights archive and set both paths before launching:

```powershell
python -m pip install -r requirements-vision.txt
$env:EXAM_DEVICE_MODEL = 'C:\models\frozen_inference_graph.pb'
$env:EXAM_DEVICE_CONFIG = 'C:\models\ssd_mobilenet_v2_coco_2018_03_29.pbtxt'
python app.py
```

When enabled, the browser sends periodic webcam samples for local server inference. The server saves flagged captures for authenticated faculty and admin review. Model files are separate downloads. The default launch uses demo accounts and binds to localhost.

## Administration

Sign in with the Admin demo account to add, edit, disable, and delete accounts, maintain the subject directory, assign exams to active students, and view analytics. Subject records form an administrative directory. Existing exams and bank questions retain their subject text.

An assigned exam can be limited to selected students. The optional assignment deadline is a last-start time, and students with existing attempts keep their original duration. Exam and account deletion protects existing academic records. Use Archive for exams with attempts and Disable for accounts with academic records.

Faculty can review results, adjust per-question marks, and inspect recorded proctoring warnings. The server counts warnings and can submit an attempt at the configured limit.
