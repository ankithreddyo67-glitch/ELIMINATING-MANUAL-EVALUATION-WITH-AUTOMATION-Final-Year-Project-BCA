"""SQLite database initialization, schema management, and initial demo seed data."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from backend.auth import hash_password
from backend.config import DB_PATH
from backend.cv_proctor import compute_integrity_summary
from backend.nlp_evaluator import compute_grade_letter, evaluate_answer


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with row_factory and foreign keys enabled."""
    target = db_path or DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


QUESTION_COLUMNS = """
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    order_index INTEGER NOT NULL DEFAULT 1,
    question_type TEXT NOT NULL CHECK(question_type IN ('MCQ', 'TRUE_FALSE', 'SHORT', 'SUBJECTIVE', 'PROGRAMMING')),
    prompt TEXT NOT NULL,
    options_json TEXT NOT NULL DEFAULT '[]',
    model_answer TEXT NOT NULL,
    keywords_json TEXT NOT NULL DEFAULT '[]',
    max_marks REAL NOT NULL DEFAULT 5.0,
    subject TEXT NOT NULL DEFAULT '',
    difficulty TEXT NOT NULL DEFAULT 'MEDIUM'
"""

SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('ADMIN', 'FACULTY', 'STUDENT')),
    department TEXT DEFAULT 'Computer Science',
    enrollment_no TEXT DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    duration_minutes INTEGER NOT NULL DEFAULT 30,
    passing_percentage REAL NOT NULL DEFAULT 40.0,
    proctoring_enabled INTEGER NOT NULL DEFAULT 1,
    proctoring_strictness TEXT NOT NULL DEFAULT 'MEDIUM' CHECK(proctoring_strictness IN ('LOW', 'MEDIUM', 'HIGH')),
    max_warnings INTEGER NOT NULL DEFAULT 5,
    auto_submit_on_warning_limit INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'PUBLISHED' CHECK(status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')),
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    faculty_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS exam_assignments (
    exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    due_at TEXT,
    PRIMARY KEY (exam_id, student_id)
);

CREATE TABLE IF NOT EXISTS questions ({QUESTION_COLUMNS});

CREATE TABLE IF NOT EXISTS question_bank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_by INTEGER NOT NULL REFERENCES users(id),
    question_type TEXT NOT NULL,
    prompt TEXT NOT NULL,
    options_json TEXT NOT NULL,
    model_answer TEXT NOT NULL,
    keywords_json TEXT NOT NULL,
    max_marks REAL NOT NULL,
    subject TEXT NOT NULL,
    difficulty TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exam_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'IN_PROGRESS'
        CHECK(status IN ('IN_PROGRESS', 'SUBMITTED', 'EVALUATED', 'PUBLISHED')),
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    submitted_at TEXT,
    evaluated_at TEXT,
    objective_score REAL NOT NULL DEFAULT 0.0,
    subjective_score REAL NOT NULL DEFAULT 0.0,
    total_score REAL NOT NULL DEFAULT 0.0,
    max_score REAL NOT NULL DEFAULT 0.0,
    percentage REAL NOT NULL DEFAULT 0.0,
    grade TEXT NOT NULL DEFAULT '-',
    passed INTEGER NOT NULL DEFAULT 0,
    integrity_score REAL NOT NULL DEFAULT 100.0,
    risk_level TEXT NOT NULL DEFAULT 'CLEAR',
    warning_count INTEGER NOT NULL DEFAULT 0,
    termination_reason TEXT NOT NULL DEFAULT '',
    faculty_remarks TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL REFERENCES exam_attempts(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    student_answer TEXT NOT NULL DEFAULT '',
    ai_marks REAL NOT NULL DEFAULT 0.0,
    final_marks REAL NOT NULL DEFAULT 0.0,
    ai_confidence REAL NOT NULL DEFAULT 1.0,
    needs_review INTEGER NOT NULL DEFAULT 0,
    ai_feedback TEXT NOT NULL DEFAULT '',
    ai_breakdown_json TEXT NOT NULL DEFAULT '{{}}',
    faculty_override INTEGER NOT NULL DEFAULT 0,
    faculty_comment TEXT NOT NULL DEFAULT '',
    UNIQUE(attempt_id, question_id)
);

CREATE TABLE IF NOT EXISTS proctor_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL REFERENCES exam_attempts(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'LOW' CHECK(severity IN ('LOW', 'MEDIUM', 'HIGH')),
    details TEXT NOT NULL DEFAULT '',
    snapshot_url TEXT,
    metrics_json TEXT NOT NULL DEFAULT '{{}}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL DEFAULT '',
    target_id INTEGER,
    details TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _migrate_questions(conn: sqlite3.Connection) -> None:
    schema = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'questions'").fetchone()["sql"]
    if "TRUE_FALSE" in schema:
        return

    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(f"CREATE TABLE questions_new ({QUESTION_COLUMNS})")
        conn.execute(
            """
            INSERT INTO questions_new (
                id, exam_id, order_index, question_type, prompt, options_json,
                model_answer, keywords_json, max_marks, subject
            )
            SELECT q.id, q.exam_id, q.order_index, q.question_type, q.prompt, q.options_json,
                   q.model_answer, q.keywords_json, q.max_marks, e.subject
            FROM questions q JOIN exams e ON e.id = q.exam_id
            """
        )
        conn.execute("DROP TABLE questions")
        conn.execute("ALTER TABLE questions_new RENAME TO questions")
        if conn.execute("PRAGMA foreign_key_check").fetchone():
            raise sqlite3.IntegrityError("Question migration would break an existing reference.")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def init_db(db_path: Path | None = None, seed: bool = True) -> None:
    """Initialize database tables and optionally populate demo seed records."""
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        _migrate_questions(conn)
        _ensure_column(conn, "users", "phone", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "exams", "restricted", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "exams", "opens_at", "TEXT")
        _ensure_column(conn, "exams", "closes_at", "TEXT")
        _ensure_column(conn, "exams", "max_warnings", "INTEGER NOT NULL DEFAULT 5")
        _ensure_column(conn, "exams", "auto_submit_on_warning_limit", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(conn, "exam_attempts", "warning_count", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "exam_attempts", "termination_reason", "TEXT NOT NULL DEFAULT ''")
        conn.commit()
        if seed:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()
            if row and row["cnt"] == 0:
                seed_demo_data(conn)
                conn.execute(
                    """
                    INSERT INTO question_bank (
                        created_by, question_type, prompt, options_json, model_answer,
                        keywords_json, max_marks, subject, difficulty
                    )
                    SELECT e.created_by, q.question_type, q.prompt, q.options_json,
                           q.model_answer, q.keywords_json, q.max_marks, e.subject, q.difficulty
                    FROM questions q JOIN exams e ON e.id = q.exam_id
                    """
                )
                conn.commit()
    finally:
        conn.close()


def seed_demo_data(conn: sqlite3.Connection) -> None:
    """Populate realistic users, exams, questions, attempts, and proctor logs."""
    users = [
        ("System Administrator", "admin@examai.edu", hash_password("Admin@123"), "ADMIN", "Academic Computing", "ADM-001"),
        ("Dr. Meera Nair", "faculty@examai.edu", hash_password("Faculty@123"), "FACULTY", "AI & Data Science", "FAC-104"),
        ("Aarav Sharma", "student1@examai.edu", hash_password("Student@123"), "STUDENT", "Computer Science", "CS2026-001"),
        ("Priya Patel", "student2@examai.edu", hash_password("Student@123"), "STUDENT", "Computer Science", "CS2026-002"),
        ("Rohan Verma", "student3@examai.edu", hash_password("Student@123"), "STUDENT", "Computer Science", "CS2026-003"),
    ]
    conn.executemany(
        """
        INSERT INTO users (full_name, email, password_hash, role, department, enrollment_no)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        users,
    )

    faculty_id = conn.execute("SELECT id FROM users WHERE email = 'faculty@examai.edu'").fetchone()["id"]
    student2_id = conn.execute("SELECT id FROM users WHERE email = 'student2@examai.edu'").fetchone()["id"]
    student3_id = conn.execute("SELECT id FROM users WHERE email = 'student3@examai.edu'").fetchone()["id"]

    # Exam 1: AI & Machine Learning
    cur = conn.execute(
        """
        INSERT INTO exams (title, subject, description, duration_minutes, passing_percentage, proctoring_enabled, proctoring_strictness, status, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Artificial Intelligence & Machine Learning Assessment",
            "CS401 - AI & ML",
            "Comprehensive evaluation covering supervised learning, regularization, NLP similarity models, and neural optimization.",
            30,
            40.0,
            1,
            "MEDIUM",
            "PUBLISHED",
            faculty_id,
        ),
    )
    exam1_id = cur.lastrowid

    exam1_questions = [
        (
            exam1_id,
            1,
            "MCQ",
            "Which evaluation metric is most reliable when classifying a highly imbalanced dataset (e.g., 2% fraud cases)?",
            json.dumps([
                "A. Raw Classification Accuracy",
                "B. Precision-Recall F1 Score",
                "C. Mean Squared Error",
                "D. R-Squared Coefficient",
            ]),
            "B",
            json.dumps(["F1", "imbalanced"]),
            5.0,
        ),
        (
            exam1_id,
            2,
            "MCQ",
            "In Natural Language Processing, why does TF-IDF downweight frequently occurring words across a corpus?",
            json.dumps([
                "A. To increase vector dimensionality",
                "B. To reduce the influence of common words with low discriminative value",
                "C. To convert supervised tasks into clustering",
                "D. To eliminate punctuation marks",
            ]),
            "B",
            json.dumps(["TF-IDF", "discriminative"]),
            5.0,
        ),
        (
            exam1_id,
            3,
            "SHORT",
            "Define 'Overfitting' in machine learning in 1-2 concise sentences.",
            json.dumps([]),
            "Overfitting occurs when a model learns noise and specific patterns from training data too closely, resulting in high training accuracy but poor generalization on unseen test data.",
            json.dumps(["training data", "noise", "generalization", "unseen"]),
            5.0,
        ),
        (
            exam1_id,
            4,
            "SUBJECTIVE",
            "Explain the difference between Supervised and Unsupervised Learning, and give one practical real-world use case for each.",
            json.dumps([]),
            "Supervised learning trains models using labeled input-output pairs to predict outcomes such as spam detection, exam score prediction, or medical diagnosis. Unsupervised learning discovers hidden structure or clusters in unlabeled data without predefined target labels, such as customer segmentation or anomaly detection.",
            json.dumps(["labeled", "unlabeled", "predict", "clusters", "spam", "segmentation"]),
            10.0,
        ),
        (
            exam1_id,
            5,
            "SUBJECTIVE",
            "Describe how an AI-powered automated answer evaluation system eliminates manual grading bias and speeds up academic result generation.",
            json.dumps([]),
            "An AI automated evaluation system uses NLP preprocessing, TF-IDF cosine similarity, and rubric concept matching to grade subjective answers consistently against a reference model answer. This reduces human fatigue and grading inconsistency, automatically calculates marks, provides instant transparent feedback, and allows faculty to review low-confidence cases.",
            json.dumps(["NLP", "cosine similarity", "rubric", "consistent", "manual", "feedback"]),
            10.0,
        ),
    ]
    conn.executemany(
        """
        INSERT INTO questions (exam_id, order_index, question_type, prompt, options_json, model_answer, keywords_json, max_marks)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        exam1_questions,
    )

    # Exam 2: Software Engineering & Computer Vision
    cur2 = conn.execute(
        """
        INSERT INTO exams (title, subject, description, duration_minutes, passing_percentage, proctoring_enabled, proctoring_strictness, status, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Full-Stack Engineering & Computer Vision Quiz",
            "CS405 - Software Systems",
            "Covers REST APIs, database normalization, and automated examination proctoring pipelines.",
            25,
            40.0,
            1,
            "HIGH",
            "PUBLISHED",
            faculty_id,
        ),
    )
    exam2_id = cur2.lastrowid

    exam2_questions = [
        (
            exam2_id,
            1,
            "MCQ",
            "Which HTTP status code appropriately indicates that a client request failed authentication due to an invalid or expired token?",
            json.dumps(["A. 200 OK", "B. 401 Unauthorized", "C. 404 Not Found", "D. 500 Internal Server Error"]),
            "B",
            json.dumps(["401"]),
            5.0,
        ),
        (
            exam2_id,
            2,
            "MCQ",
            "During automated webcam proctoring, which computer vision signal directly indicates potential collaboration or unauthorized assistance?",
            json.dumps([
                "A. Stable single face centered in frame",
                "B. Multiple faces detected simultaneously in the camera view",
                "C. Normal ambient room lighting",
                "D. Steady keyboard typing cadence",
            ]),
            "B",
            json.dumps(["multiple faces"]),
            5.0,
        ),
        (
            exam2_id,
            3,
            "SUBJECTIVE",
            "How does combining Computer Vision webcam monitoring with browser telemetry (tab switching, fullscreen checks) improve academic integrity during online exams?",
            json.dumps([]),
            "Computer vision continuously monitors candidate presence, detects multiple faces, camera occlusion, and gaze deviation, while browser telemetry logs tab switches, window blur, and copy-paste attempts. Combining both signals yields an objective integrity score and timestamped evidence for faculty verification.",
            json.dumps(["presence", "multiple faces", "gaze", "tab", "integrity score"]),
            10.0,
        ),
        (
            exam2_id,
            4,
            "SUBJECTIVE",
            "Why is role-based access control (RBAC) essential in an automated examination platform?",
            json.dumps([]),
            "Role-based access control separates permissions between students, faculty, and administrators so students cannot view model answers or modify marks, faculty can author rubrics and override grades, and administrators oversee audit logs and user accounts securely.",
            json.dumps(["permissions", "students", "faculty", "model answers", "audit"]),
            5.0,
        ),
    ]
    conn.executemany(
        """
        INSERT INTO questions (exam_id, order_index, question_type, prompt, options_json, model_answer, keywords_json, max_marks)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        exam2_questions,
    )

    # Seed two evaluated attempts for Exam 1 so Faculty/Admin dashboards are rich immediately
    q_rows = conn.execute(
        "SELECT * FROM questions WHERE exam_id = ? ORDER BY order_index", (exam1_id,)
    ).fetchall()

    _seed_attempt(
        conn,
        exam_id=exam1_id,
        student_id=student2_id,
        questions=q_rows,
        answers_map={
            1: "B",
            2: "B",
            3: "Overfitting happens when a machine learning model memorizes noise in the training data and fails to generalize well to unseen test data.",
            4: "Supervised learning uses labeled training data with input-output pairs to predict outcomes such as email spam classification. Unsupervised learning discovers hidden clusters and patterns in unlabeled data, such as customer segmentation.",
            5: "AI automated evaluation uses NLP, TF-IDF cosine similarity, and rubric concept coverage to grade answers consistently against model answers. It removes human fatigue, computes marks automatically, generates transparent feedback, and flags low-confidence responses for faculty review.",
        },
        proctor_events=[
            ("EXAM_STARTED", "LOW", "Webcam & fullscreen verified."),
            ("LOOKING_AWAY", "LOW", "Brief gaze offset detected (offset=0.26)."),
            ("EXAM_SUBMITTED", "LOW", "Candidate submitted exam normally."),
        ],
        publish=True,
        faculty_remarks="Excellent conceptual clarity and crisp examples.",
    )

    _seed_attempt(
        conn,
        exam_id=exam1_id,
        student_id=student3_id,
        questions=q_rows,
        answers_map={
            1: "A",
            2: "B",
            3: "Overfitting means the model works on training data.",
            4: "Supervised learning has labels for prediction while unsupervised learning does not use labels.",
            5: "Automated systems check keywords with NLP so manual grading is faster and more consistent.",
        },
        proctor_events=[
            ("EXAM_STARTED", "LOW", "Exam session initialized."),
            ("TAB_SWITCH", "HIGH", "Browser tab lost visibility for 6 seconds."),
            ("NO_FACE", "MEDIUM", "No candidate face detected in webcam frame."),
            ("TAB_SWITCH", "HIGH", "Browser tab lost visibility for 4 seconds."),
            ("LOOKING_AWAY", "LOW", "Head shifted off-center."),
        ],
        publish=False,
        faculty_remarks="Pending faculty review due to tab switches and brief answers.",
    )

    conn.execute(
        """
        INSERT INTO audit_logs (actor_id, action, target_type, target_id, details)
        VALUES (?, ?, ?, ?, ?)
        """,
        (faculty_id, "SEED_INITIALIZED", "EXAM", exam1_id, "Initialized demo exams, questions, and sample evaluations."),
    )
    conn.commit()


def _seed_attempt(
    conn: sqlite3.Connection,
    exam_id: int,
    student_id: int,
    questions: list[sqlite3.Row],
    answers_map: dict[int, str],
    proctor_events: list[tuple[str, str, str]],
    publish: bool,
    faculty_remarks: str,
) -> None:
    """Create and auto-evaluate a seeded exam attempt."""
    cur = conn.execute(
        """
        INSERT INTO exam_attempts (exam_id, student_id, status, started_at, submitted_at, evaluated_at, faculty_remarks)
        VALUES (?, ?, ?, datetime('now', '-2 hours'), datetime('now', '-90 minutes'), datetime('now', '-85 minutes'), ?)
        """,
        (exam_id, student_id, "PUBLISHED" if publish else "EVALUATED", faculty_remarks),
    )
    attempt_id = cur.lastrowid

    obj_score = 0.0
    subj_score = 0.0
    max_score = 0.0

    for q in questions:
        idx = q["order_index"]
        ans_text = answers_map.get(idx, "")
        keywords = json.loads(q["keywords_json"])
        res = evaluate_answer(
            q["question_type"],
            ans_text,
            q["model_answer"],
            keywords,
            q["max_marks"],
        )
        max_score += float(q["max_marks"])
        if q["question_type"] == "MCQ":
            obj_score += res["awarded_marks"]
        else:
            subj_score += res["awarded_marks"]

        conn.execute(
            """
            INSERT INTO answers (
                attempt_id, question_id, student_answer, ai_marks, final_marks,
                ai_confidence, needs_review, ai_feedback, ai_breakdown_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                q["id"],
                ans_text,
                res["awarded_marks"],
                res["awarded_marks"],
                res["confidence"],
                1 if res["needs_review"] else 0,
                res["feedback"],
                json.dumps(res["breakdown"]),
            ),
        )

    total_score = round(obj_score + subj_score, 2)
    pct = round((total_score / max_score * 100.0) if max_score > 0 else 0.0, 2)
    grade = compute_grade_letter(pct)
    passed = 1 if pct >= 40.0 else 0

    for etype, sev, details in proctor_events:
        conn.execute(
            """
            INSERT INTO proctor_logs (attempt_id, event_type, severity, details)
            VALUES (?, ?, ?, ?)
            """,
            (attempt_id, etype, sev, details),
        )

    integrity = compute_integrity_summary(
        [{"event_type": e[0], "severity": e[1]} for e in proctor_events],
        strictness="MEDIUM",
    )

    conn.execute(
        """
        UPDATE exam_attempts
        SET objective_score = ?, subjective_score = ?, total_score = ?, max_score = ?,
            percentage = ?, grade = ?, passed = ?, integrity_score = ?, risk_level = ?,
            warning_count = ?
        WHERE id = ?
        """,
        (
            round(obj_score, 2),
            round(subj_score, 2),
            total_score,
            round(max_score, 2),
            pct,
            grade,
            passed,
            integrity["integrity_score"],
            integrity["risk_level"],
            integrity["warning_count"],
            attempt_id,
        ),
    )
