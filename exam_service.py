"""Business logic for users, exams, attempts, AI evaluation, proctoring, and analytics."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
import json
import math
import random
import sqlite3
from typing import Any

from backend.auth import create_token, hash_password, verify_password
from backend.config import DEFAULT_MAX_WARNINGS_BY_STRICTNESS, SEVERITY_BY_EVENT
from backend.cv_proctor import (
    compute_integrity_summary,
    device_detection_enabled,
    evaluate_cv_telemetry,
    save_snapshot_if_flagged,
)
from backend.nlp_evaluator import compute_grade_letter, evaluate_answer


class ServiceError(Exception):
    """Domain error mapped to HTTP status codes by the router."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _log_audit(
    conn: sqlite3.Connection,
    actor_id: int | None,
    action: str,
    target_type: str = "",
    target_id: int | None = None,
    details: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO audit_logs (actor_id, action, target_type, target_id, details)
        VALUES (?, ?, ?, ?, ?)
        """,
        (actor_id, action, target_type, target_id, details),
    )


def register_user(conn: sqlite3.Connection, data: dict[str, Any], admin_id: int | None = None) -> dict[str, Any]:
    """Register a new student or faculty user."""
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = (data.get("role") or "STUDENT").strip().upper()
    department = (data.get("department") or "Computer Science").strip()
    enrollment_no = (data.get("enrollment_no") or "").strip()

    if len(full_name) < 2:
        raise ServiceError("Full name must be at least 2 characters.")
    if "@" not in email or "." not in email:
        raise ServiceError("Valid email address is required.")
    if len(password) < 6:
        raise ServiceError("Password must be at least 6 characters.")
    allowed_roles = ("STUDENT", "FACULTY", "ADMIN") if admin_id else ("STUDENT", "FACULTY")
    if role not in allowed_roles:
        raise ServiceError("Self-registration is allowed for STUDENT or FACULTY roles only.")

    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        raise ServiceError("An account with this email already exists.", status_code=409)

    cur = conn.execute(
        """
        INSERT INTO users (full_name, email, password_hash, role, department, enrollment_no)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (full_name, email, hash_password(password), role, department, enrollment_no),
    )
    user_id = cur.lastrowid
    conn.execute("UPDATE users SET phone = ? WHERE id = ?", (str(data.get("phone") or "").strip(), user_id))
    _log_audit(conn, admin_id or user_id, "USER_REGISTERED", "USER", user_id, f"Registered as {role}")
    conn.commit()

    user = dict(
        conn.execute(
            "SELECT id, full_name, email, role, department, enrollment_no, is_active, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    )
    return {"user": user, "token": create_token(user)}


def authenticate_user(conn: sqlite3.Connection, email: str, password: str) -> dict[str, Any]:
    """Authenticate credentials and issue bearer token."""
    clean_email = (email or "").strip().lower()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (clean_email,)).fetchone()
    if not row or not verify_password(password or "", row["password_hash"]):
        raise ServiceError("Invalid email or password.", status_code=401)
    if not row["is_active"]:
        raise ServiceError("Account is disabled. Contact administrator.", status_code=403)

    user = {
        "id": row["id"],
        "full_name": row["full_name"],
        "email": row["email"],
        "role": row["role"],
        "department": row["department"],
        "enrollment_no": row["enrollment_no"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
    }
    return {"user": user, "token": create_token(user)}


def list_users(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, full_name, email, role, department, enrollment_no, phone, is_active, created_at
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def update_user_status_or_role(
    conn: sqlite3.Connection, actor_id: int, target_user_id: int, payload: dict[str, Any]
) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (target_user_id,)).fetchone()
    if not row:
        raise ServiceError("User not found.", status_code=404)

    role = (payload.get("role") or row["role"]).upper()
    if role not in ("ADMIN", "FACULTY", "STUDENT"):
        raise ServiceError("Invalid role.")
    is_active = int(bool(payload["is_active"])) if "is_active" in payload else row["is_active"]

    if actor_id == target_user_id and (role != row["role"] or not is_active):
        raise ServiceError("You cannot disable or change your own administrator role.")
    name = str(payload.get("full_name", row["full_name"])).strip()
    email = str(payload.get("email", row["email"])).strip().lower()
    password = payload.get("password") or ""
    if len(name) < 2 or "@" not in email or "." not in email:
        raise ServiceError("A valid name and email are required.")
    if password and (not isinstance(password, str) or len(password) < 6):
        raise ServiceError("Password must be at least 6 characters.")
    if conn.execute("SELECT 1 FROM users WHERE email = ? AND id != ?", (email, target_user_id)).fetchone():
        raise ServiceError("Email already in use.", 409)
    conn.execute(
        """UPDATE users SET role = ?, is_active = ?, full_name = ?, email = ?,
           department = ?, phone = ?, password_hash = ? WHERE id = ?""",
        (role, is_active, name, email, str(payload.get("department", row["department"])).strip(),
         str(payload.get("phone", row["phone"])).strip(),
         hash_password(password) if password else row["password_hash"], target_user_id),
    )
    _log_audit(
        conn,
        actor_id,
        "USER_UPDATED",
        "USER",
        target_user_id,
        f"Updated role={role}, active={bool(is_active)}",
    )
    conn.commit()
    updated = conn.execute(
        "SELECT id, full_name, email, role, department, enrollment_no, is_active, created_at FROM users WHERE id = ?",
        (target_user_id,),
    ).fetchone()
    return dict(updated)


def list_exams(conn: sqlite3.Connection, user: dict[str, Any]) -> list[dict[str, Any]]:
    """List exams with question count, total marks, and student attempt summary if applicable."""
    role = user["role"]
    if role == "STUDENT":
        rows = conn.execute(
            """
            SELECT e.*, u.full_name AS creator_name,
                   (SELECT COUNT(*) FROM questions q WHERE q.exam_id = e.id) AS question_count,
                   (SELECT COALESCE(SUM(max_marks), 0) FROM questions q WHERE q.exam_id = e.id) AS total_marks
            FROM exams e
            JOIN users u ON u.id = e.created_by
            WHERE e.status = 'PUBLISHED' AND (
                e.restricted = 0 OR EXISTS (SELECT 1 FROM exam_assignments a
                WHERE a.exam_id = e.id AND a.student_id = ?)
                OR EXISTS (SELECT 1 FROM exam_attempts a WHERE a.exam_id = e.id AND a.student_id = ?)
            )
            ORDER BY e.id DESC
            """, (user["uid"], user["uid"]),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT e.*, u.full_name AS creator_name,
                   (SELECT COUNT(*) FROM questions q WHERE q.exam_id = e.id) AS question_count,
                   (SELECT COALESCE(SUM(max_marks), 0) FROM questions q WHERE q.exam_id = e.id) AS total_marks,
                   (SELECT COUNT(*) FROM exam_attempts a WHERE a.exam_id = e.id) AS attempt_count
            FROM exams e
            JOIN users u ON u.id = e.created_by
            ORDER BY e.id DESC
            """
        ).fetchall()

    exams = [dict(r) for r in rows]
    if role == "STUDENT":
        for ex in exams:
            att = conn.execute(
                """
                SELECT id, status, total_score, max_score, percentage, grade, passed, integrity_score, risk_level
                FROM exam_attempts
                WHERE exam_id = ? AND student_id = ?
                ORDER BY id DESC LIMIT 1
                """,
                (ex["id"], user["uid"]),
            ).fetchone()
            ex["my_attempt"] = dict(att) if att else None
            if ex["restricted"]:
                assignment = conn.execute(
                    "SELECT due_at FROM exam_assignments WHERE exam_id = ? AND student_id = ?",
                    (ex["id"], user["uid"]),
                ).fetchone()
                ex["assignment_due_at"] = assignment["due_at"] if assignment else None
    return exams


def get_exam_detail(conn: sqlite3.Connection, exam_id: int, include_answers: bool) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT e.*, u.full_name AS creator_name
        FROM exams e
        JOIN users u ON u.id = e.created_by
        WHERE e.id = ?
        """,
        (exam_id,),
    ).fetchone()
    if not row:
        raise ServiceError("Exam not found.", status_code=404)

    q_rows = conn.execute(
        "SELECT * FROM questions WHERE exam_id = ? ORDER BY order_index, id",
        (exam_id,),
    ).fetchall()
    questions: list[dict[str, Any]] = []
    total_marks = 0.0
    for q in q_rows:
        total_marks += float(q["max_marks"])
        item: dict[str, Any] = {
            "id": q["id"],
            "exam_id": q["exam_id"],
            "order_index": q["order_index"],
            "question_type": q["question_type"],
            "prompt": q["prompt"],
            "options": json.loads(q["options_json"]),
            "max_marks": q["max_marks"],
            "subject": q["subject"] or row["subject"],
            "difficulty": q["difficulty"],
        }
        if include_answers:
            item["model_answer"] = q["model_answer"]
            item["keywords"] = json.loads(q["keywords_json"])
        questions.append(item)

    exam = dict(row)
    exam["total_marks"] = round(total_marks, 2)
    exam["questions"] = questions
    return exam


QUESTION_FIELDS = (
    "question_type", "prompt", "options_json", "model_answer",
    "keywords_json", "max_marks", "subject", "difficulty",
)
DIFFICULTIES = {"EASY", "MEDIUM", "HARD"}


def _question_values(data: dict[str, Any], default_subject: str = "") -> tuple:
    if not isinstance(data, dict):
        raise ServiceError("Each question must be an object.")
    kind = str(data.get("question_type") or "SUBJECTIVE").upper()
    prompt = str(data.get("prompt") or "").strip()
    answer = str(data.get("model_answer") or "").rstrip()
    subject = str(data.get("subject") or default_subject).strip()
    difficulty = str(data.get("difficulty") or "MEDIUM").upper()
    if kind not in {"MCQ", "TRUE_FALSE", "SHORT", "SUBJECTIVE", "PROGRAMMING"}:
        raise ServiceError("Unsupported question type.")
    if not (prompt and answer.strip() and subject):
        raise ServiceError("Each question requires a subject, prompt, and reference answer.")
    if difficulty not in DIFFICULTIES:
        raise ServiceError("Difficulty must be easy, medium, or hard.")
    try:
        marks = float(data.get("max_marks", 5))
    except (TypeError, ValueError):
        raise ServiceError("Question marks must be a number.") from None
    if not math.isfinite(marks) or marks <= 0:
        raise ServiceError("Question marks must be positive and finite.")
    options = []
    if kind == "MCQ":
        options = data.get("options")
        if not isinstance(options, list) or not 2 <= len(options) <= 4:
            raise ServiceError("Multiple-choice questions require 2 to 4 options.")
        normalized = []
        for letter, option in zip("ABCD", options):
            label = str(option or "").strip()
            if label.startswith((letter + ".", letter + ")")):
                label = label[2:].strip()
            if not label:
                raise ServiceError("Fill in every multiple-choice option.")
            normalized.append(f"{letter}. {label}")
        options = normalized
        answer = answer.strip().upper()
        if answer not in tuple("ABCD"[:len(options)]):
            raise ServiceError("The answer key must match an option letter.")
    elif kind == "TRUE_FALSE":
        options = ["True", "False"]
        answer = answer.strip().lower().capitalize()
        if answer not in options:
            raise ServiceError("Choose True or False as the reference answer.")
    keywords = data.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [word.strip() for word in keywords.split(",") if word.strip()]
    if not isinstance(keywords, list) or not all(isinstance(word, str) for word in keywords):
        raise ServiceError("Rubric concepts must be text.")
    if kind != "PROGRAMMING":
        answer = answer.strip()
    return kind, prompt, json.dumps(options), answer, json.dumps(keywords), marks, subject, difficulty


def list_bank_questions(conn: sqlite3.Connection, actor_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT * FROM question_bank WHERE created_by = ?
           ORDER BY subject COLLATE NOCASE, difficulty, id""",
        (actor_id,),
    )
    questions = []
    for row in rows:
        question = dict(row)
        question["options"] = json.loads(question.pop("options_json"))
        question["keywords"] = json.loads(question.pop("keywords_json"))
        questions.append(question)
    return questions


def save_bank_question(
    conn: sqlite3.Connection, actor_id: int, data: dict[str, Any], question_id: int | None = None
) -> int:
    values = _question_values(data)
    if question_id is None:
        result = conn.execute(
            """INSERT INTO question_bank (
                question_type, prompt, options_json, model_answer, keywords_json,
                max_marks, subject, difficulty, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (*values, actor_id),
        )
        question_id = result.lastrowid
    else:
        result = conn.execute(
            """UPDATE question_bank SET question_type = ?, prompt = ?, options_json = ?,
                model_answer = ?, keywords_json = ?, max_marks = ?, subject = ?, difficulty = ?
               WHERE id = ? AND created_by = ?""",
            (*values, question_id, actor_id),
        )
        if not result.rowcount:
            raise ServiceError("Bank question not found.", 404)
    conn.commit()
    return question_id


def delete_bank_question(conn: sqlite3.Connection, actor_id: int, question_id: int) -> None:
    result = conn.execute(
        "DELETE FROM question_bank WHERE id = ? AND created_by = ?", (question_id, actor_id)
    )
    if not result.rowcount:
        raise ServiceError("Bank question not found.", 404)
    conn.commit()


def _bank_paper(conn: sqlite3.Connection, actor_id: int, data: dict[str, Any]) -> list[tuple]:
    bank = list_bank_questions(conn, actor_id)
    selected_ids = data.get("bank_question_ids") or []
    sample = data.get("random_selection")
    if not isinstance(selected_ids, list) or any(type(item) is not int for item in selected_ids):
        raise ServiceError("Choose valid question bank entries.")
    if len(set(selected_ids)) != len(selected_ids):
        raise ServiceError("Select each question only once.")
    if sample is not None:
        if not isinstance(sample, dict) or selected_ids:
            raise ServiceError("Choose either a random paper or individual bank questions.")
        count = sample.get("count")
        if type(count) is not int or not 1 <= count <= 100:
            raise ServiceError("Random paper size must be between 1 and 100.")
        subject = str(sample.get("subject") or "").strip().casefold()
        difficulty = str(sample.get("difficulty") or "").upper()
        if difficulty and difficulty not in DIFFICULTIES:
            raise ServiceError("Invalid difficulty filter.")
        pool = [
            q for q in bank if (not subject or q["subject"].casefold() == subject)
            and (not difficulty or q["difficulty"] == difficulty)
        ]
        if len(pool) < count:
            raise ServiceError(f"Only {len(pool)} bank questions match the selection.")
        selected = random.sample(pool, count)
    else:
        by_id = {q["id"]: q for q in bank}
        if any(item not in by_id for item in selected_ids):
            raise ServiceError("A selected bank question was not found.", 404)
        selected = [by_id[item] for item in selected_ids]
    return [_question_values(q) for q in selected]


def _schedule(data: dict[str, Any]) -> tuple[str | None, str | None]:
    def parse(value: str | None) -> str | None:
        if not value:
            return None
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if stamp.utcoffset() is None:
                raise ValueError()
            return stamp.astimezone(timezone.utc).isoformat(timespec="seconds")
        except (ValueError, AttributeError, TypeError, OverflowError):
            raise ServiceError("Use valid dates with a time zone for the exam schedule.") from None

    opens, closes = parse(data.get("opens_at")), parse(data.get("closes_at"))
    if opens and closes and opens >= closes:
        raise ServiceError("Closing time must be after opening time.")
    return opens, closes


def update_exam_schedule(
    conn: sqlite3.Connection, actor: dict[str, Any], exam_id: int, data: dict[str, Any]
) -> dict[str, Any]:
    opens, closes = _schedule(data)
    result = conn.execute(
        """UPDATE exams SET opens_at = ?, closes_at = ?
           WHERE id = ? AND (created_by = ? OR ? = 'ADMIN')""",
        (opens, closes, exam_id, actor["uid"], actor["role"]),
    )
    if not result.rowcount:
        raise ServiceError("Exam not found.", 404)
    _log_audit(conn, actor["uid"], "EXAM_SCHEDULE_UPDATED", "EXAM", exam_id)
    conn.commit()
    return get_exam_detail(conn, exam_id, include_answers=True)


def create_exam(conn: sqlite3.Connection, actor_id: int, data: dict[str, Any]) -> dict[str, Any]:
    """Create a new exam with questions and rubric definitions."""
    title = (data.get("title") or "").strip()
    subject = (data.get("subject") or "").strip()
    description = (data.get("description") or "").strip()
    duration = int(data.get("duration_minutes") or 30)
    passing_pct = float(data.get("passing_percentage") or 40.0)
    proctoring_enabled = 1 if data.get("proctoring_enabled", True) else 0
    strictness = (data.get("proctoring_strictness") or "MEDIUM").upper()
    max_warnings = int(data.get("max_warnings") or DEFAULT_MAX_WARNINGS_BY_STRICTNESS.get(strictness, 5))
    auto_submit_limit = 1 if data.get("auto_submit_on_warning_limit", True) else 0
    status = (data.get("status") or "PUBLISHED").upper()
    questions = data.get("questions") or []

    if len(title) < 3 or len(subject) < 2:
        raise ServiceError("Exam title and subject are required.")
    if duration < 1 or duration > 360:
        raise ServiceError("Duration must be between 1 and 360 minutes.")
    if strictness not in ("LOW", "MEDIUM", "HIGH"):
        raise ServiceError("Proctoring strictness must be LOW, MEDIUM, or HIGH.")
    if max_warnings < 1 or max_warnings > 50:
        raise ServiceError("Max warnings must be between 1 and 50.")
    if status not in ("DRAFT", "PUBLISHED", "ARCHIVED"):
        raise ServiceError("Invalid exam status.")
    if not isinstance(questions, list):
        raise ServiceError("Questions must be a list.")
    opens, closes = _schedule(data)
    paper = [_question_values(q, subject) for q in questions]
    paper.extend(_bank_paper(conn, actor_id, data))
    if not 1 <= len(paper) <= 100:
        raise ServiceError("An exam requires between 1 and 100 questions.")

    cur = conn.execute(
        """
        INSERT INTO exams (
            title, subject, description, duration_minutes, passing_percentage,
            proctoring_enabled, proctoring_strictness, max_warnings, auto_submit_on_warning_limit,
            status, created_by, opens_at, closes_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title, subject, description, duration, passing_pct,
            proctoring_enabled, strictness, max_warnings, auto_submit_limit,
            status, actor_id, opens, closes,
        ),
    )
    exam_id = cur.lastrowid
    _insert_paper(conn, exam_id, paper)

    _log_audit(conn, actor_id, "EXAM_CREATED", "EXAM", exam_id, f"Created '{title}' with {len(paper)} questions.")
    conn.commit()
    return get_exam_detail(conn, exam_id, include_answers=True)


def _insert_paper(conn: sqlite3.Connection, exam_id: int, paper: list[tuple]) -> None:
    conn.executemany(
        f"""INSERT INTO questions (exam_id, order_index, {", ".join(QUESTION_FIELDS)})
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(exam_id, index, *values) for index, values in enumerate(paper, start=1)],
    )


def update_draft_paper(
    conn: sqlite3.Connection, actor: dict[str, Any], exam_id: int, data: dict[str, Any]
) -> dict[str, Any]:
    questions = data.get("questions")
    if not isinstance(questions, list) or not 1 <= len(questions) <= 100:
        raise ServiceError("A paper requires between 1 and 100 questions.")
    conn.execute("BEGIN IMMEDIATE")
    exam = conn.execute(
        "SELECT subject, status, created_by FROM exams WHERE id = ?", (exam_id,)
    ).fetchone()
    if not exam or (exam["created_by"] != actor["uid"] and actor["role"] != "ADMIN"):
        raise ServiceError("Exam not found.", 404)
    if exam["status"] != "DRAFT" or conn.execute(
        "SELECT 1 FROM exam_attempts WHERE exam_id = ? LIMIT 1", (exam_id,)
    ).fetchone():
        raise ServiceError("Only draft papers without attempts can be edited.", 409)
    paper = [_question_values(question, exam["subject"]) for question in questions]
    conn.execute("DELETE FROM questions WHERE exam_id = ?", (exam_id,))
    _insert_paper(conn, exam_id, paper)
    _log_audit(conn, actor["uid"], "EXAM_PAPER_UPDATED", "EXAM", exam_id)
    conn.commit()
    return get_exam_detail(conn, exam_id, include_answers=True)


def update_exam_status(conn: sqlite3.Connection, actor_id: int, exam_id: int, status: str) -> dict[str, Any]:
    clean = (status or "").upper()
    if clean not in ("DRAFT", "PUBLISHED", "ARCHIVED"):
        raise ServiceError("Invalid status.")
    row = conn.execute("SELECT id FROM exams WHERE id = ?", (exam_id,)).fetchone()
    if not row:
        raise ServiceError("Exam not found.", status_code=404)
    conn.execute("UPDATE exams SET status = ? WHERE id = ?", (clean, exam_id))
    _log_audit(conn, actor_id, "EXAM_STATUS_UPDATED", "EXAM", exam_id, f"Status set to {clean}")
    conn.commit()
    return get_exam_detail(conn, exam_id, include_answers=True)


def start_attempt(conn: sqlite3.Connection, exam_id: int, student_id: int) -> dict[str, Any]:
    """Start or resume an in-progress exam attempt for a student."""
    conn.execute("BEGIN IMMEDIATE")
    exam = conn.execute("SELECT * FROM exams WHERE id = ?", (exam_id,)).fetchone()
    if not exam or exam["status"] != "PUBLISHED":
        raise ServiceError("Exam is not available for taking.", status_code=404)

    existing = conn.execute(
        "SELECT * FROM exam_attempts WHERE exam_id = ? AND student_id = ? ORDER BY id DESC LIMIT 1",
        (exam_id, student_id),
    ).fetchone()

    if existing:
        if existing["status"] == "IN_PROGRESS":
            conn.commit()
            return _serialize_active_attempt(conn, existing["id"])
        raise ServiceError("You have already completed this examination.", status_code=409)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if exam["restricted"]:
        assignment = conn.execute(
            "SELECT due_at FROM exam_assignments WHERE exam_id = ? AND student_id = ?", (exam_id, student_id)
        ).fetchone()
        if not assignment:
            raise ServiceError("This examination is not assigned to you.", 403)
        if assignment["due_at"] and now >= assignment["due_at"]:
            raise ServiceError("The assignment start deadline has passed.", 409)
    if exam["opens_at"] and now < exam["opens_at"]:
        raise ServiceError("This examination has not opened yet.", 409)
    if exam["closes_at"] and now >= exam["closes_at"]:
        raise ServiceError("The start window for this examination has closed.", 409)

    max_score_row = conn.execute(
        "SELECT COALESCE(SUM(max_marks), 0) AS total FROM questions WHERE exam_id = ?",
        (exam_id,),
    ).fetchone()
    max_score = float(max_score_row["total"])

    cur = conn.execute(
        """
        INSERT INTO exam_attempts (exam_id, student_id, status, max_score)
        VALUES (?, ?, 'IN_PROGRESS', ?)
        """,
        (exam_id, student_id, max_score),
    )
    attempt_id = cur.lastrowid
    conn.execute(
        """
        INSERT INTO proctor_logs (attempt_id, event_type, severity, details)
        VALUES (?, 'EXAM_STARTED', 'LOW', 'Candidate started examination session.')
        """,
        (attempt_id,),
    )
    conn.commit()
    return _serialize_active_attempt(conn, attempt_id)


def _serialize_active_attempt(conn: sqlite3.Connection, attempt_id: int) -> dict[str, Any]:
    att = conn.execute("SELECT * FROM exam_attempts WHERE id = ?", (attempt_id,)).fetchone()
    if not att:
        raise ServiceError("Attempt not found.", status_code=404)
    exam_detail = get_exam_detail(conn, att["exam_id"], include_answers=False)
    saved_rows = conn.execute(
        "SELECT question_id, student_answer FROM answers WHERE attempt_id = ?",
        (attempt_id,),
    ).fetchall()
    drafts = {r["question_id"]: r["student_answer"] for r in saved_rows}
    return {
        "attempt": dict(att),
        "exam": exam_detail,
        "saved_answers": drafts,
        "remaining_seconds": max(0, -_attempt_elapsed_past_deadline(conn, attempt_id)),
        "device_detection_enabled": device_detection_enabled(),
    }


def _attempt_elapsed_past_deadline(conn: sqlite3.Connection, attempt_id: int) -> int:
    row = conn.execute(
        """
        SELECT CAST(strftime('%s', 'now') AS INTEGER)
            - CAST(strftime('%s', a.started_at) AS INTEGER)
            - e.duration_minutes * 60 AS elapsed
        FROM exam_attempts a JOIN exams e ON e.id = a.exam_id
        WHERE a.id = ?
        """,
        (attempt_id,),
    ).fetchone()
    return int(row["elapsed"])


def save_draft_answer(
    conn: sqlite3.Connection, attempt_id: int, student_id: int, question_id: int, student_answer: str
) -> dict[str, Any]:
    att = conn.execute("SELECT * FROM exam_attempts WHERE id = ?", (attempt_id,)).fetchone()
    if not att or att["student_id"] != student_id:
        raise ServiceError("Attempt not found.", status_code=404)
    if att["status"] != "IN_PROGRESS":
        raise ServiceError("Attempt is already submitted.", status_code=409)
    if _attempt_elapsed_past_deadline(conn, attempt_id) >= 0:
        raise ServiceError("The exam time has expired.", status_code=409)

    q = conn.execute(
        "SELECT id FROM questions WHERE id = ? AND exam_id = ?",
        (question_id, att["exam_id"]),
    ).fetchone()
    if not q:
        raise ServiceError("Question does not belong to this exam.")

    conn.execute(
        """
        INSERT INTO answers (attempt_id, question_id, student_answer)
        VALUES (?, ?, ?)
        ON CONFLICT(attempt_id, question_id) DO UPDATE SET student_answer = excluded.student_answer
        """,
        (attempt_id, question_id, student_answer or ""),
    )
    conn.commit()
    return {"saved": True, "attempt_id": attempt_id, "question_id": question_id}


def submit_and_evaluate_attempt(
    conn: sqlite3.Connection,
    attempt_id: int,
    student_id: int,
    answers_payload: dict[str, str] | list[dict[str, Any]],
    auto_publish: bool = True,
) -> dict[str, Any]:
    """Save submitted answers and execute the AI/ML & NLP evaluation pipeline."""
    att = conn.execute("SELECT * FROM exam_attempts WHERE id = ?", (attempt_id,)).fetchone()
    if not att or att["student_id"] != student_id:
        raise ServiceError("Attempt not found.", status_code=404)
    if att["status"] != "IN_PROGRESS":
        raise ServiceError("Attempt has already been submitted.", status_code=409)

    if _attempt_elapsed_past_deadline(conn, attempt_id) >= 0:
        answers_payload = {}

    # Normalize answers map {question_id: text}
    ans_map: dict[int, str] = {}
    if isinstance(answers_payload, dict):
        for k, v in answers_payload.items():
            ans_map[int(k)] = str(v or "")
    elif isinstance(answers_payload, list):
        for item in answers_payload:
            ans_map[int(item["question_id"])] = str(item.get("student_answer") or "")

    for qid, ans_text in ans_map.items():
        q_exists = conn.execute(
            "SELECT id FROM questions WHERE id = ? AND exam_id = ?", (qid, att["exam_id"])
        ).fetchone()
        if q_exists:
            conn.execute(
                """
                INSERT INTO answers (attempt_id, question_id, student_answer)
                VALUES (?, ?, ?)
                ON CONFLICT(attempt_id, question_id) DO UPDATE SET student_answer = excluded.student_answer
                """,
                (attempt_id, qid, ans_text),
            )

    conn.execute(
        """
        UPDATE exam_attempts
        SET status = 'SUBMITTED', submitted_at = datetime('now')
        WHERE id = ?
        """,
        (attempt_id,),
    )
    conn.execute(
        """
        INSERT INTO proctor_logs (attempt_id, event_type, severity, details)
        VALUES (?, 'EXAM_SUBMITTED', 'LOW', 'Candidate submitted examination answers.')
        """,
        (attempt_id,),
    )
    conn.commit()

    return run_ai_evaluation_for_attempt(conn, attempt_id, auto_publish=auto_publish)


def run_ai_evaluation_for_attempt(
    conn: sqlite3.Connection,
    attempt_id: int,
    auto_publish: bool = False,
) -> dict[str, Any]:
    """Evaluate all questions of an attempt using the ML/NLP evaluation engine."""
    att = conn.execute("SELECT * FROM exam_attempts WHERE id = ?", (attempt_id,)).fetchone()
    if not att:
        raise ServiceError("Attempt not found.", status_code=404)

    exam = conn.execute("SELECT * FROM exams WHERE id = ?", (att["exam_id"],)).fetchone()
    questions = conn.execute(
        "SELECT * FROM questions WHERE exam_id = ? ORDER BY order_index, id",
        (att["exam_id"],),
    ).fetchall()

    existing_ans = {
        r["question_id"]: dict(r)
        for r in conn.execute("SELECT * FROM answers WHERE attempt_id = ?", (attempt_id,)).fetchall()
    }

    obj_score = 0.0
    subj_score = 0.0
    max_score = 0.0

    for q in questions:
        qid = q["id"]
        ans_row = existing_ans.get(qid)
        student_text = ans_row["student_answer"] if ans_row else ""

        # Gather peer responses for corpus IDF enrichment
        peer_rows = conn.execute(
            """
            SELECT a.student_answer
            FROM answers a
            JOIN exam_attempts ea ON ea.id = a.attempt_id
            WHERE a.question_id = ? AND ea.id != ? AND a.student_answer != ''
            """,
            (qid, attempt_id),
        ).fetchall()
        corpus = [r["student_answer"] for r in peer_rows]

        keywords = json.loads(q["keywords_json"])
        result = evaluate_answer(
            q["question_type"],
            student_text,
            q["model_answer"],
            keywords,
            q["max_marks"],
            corpus_answers=corpus,
        )

        # Preserve manual faculty override if already set
        if ans_row and ans_row["faculty_override"]:
            final_marks = float(ans_row["final_marks"])
        else:
            final_marks = float(result["awarded_marks"])

        max_score += float(q["max_marks"])
        if q["question_type"] in ("MCQ", "TRUE_FALSE"):
            obj_score += final_marks
        else:
            subj_score += final_marks

        conn.execute(
            """
            INSERT INTO answers (
                attempt_id, question_id, student_answer, ai_marks, final_marks,
                ai_confidence, needs_review, ai_feedback, ai_breakdown_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(attempt_id, question_id) DO UPDATE SET
                ai_marks = excluded.ai_marks,
                final_marks = CASE WHEN answers.faculty_override = 1 THEN answers.final_marks ELSE excluded.final_marks END,
                ai_confidence = excluded.ai_confidence,
                needs_review = excluded.needs_review,
                ai_feedback = excluded.ai_feedback,
                ai_breakdown_json = excluded.ai_breakdown_json
            """,
            (
                attempt_id,
                qid,
                student_text,
                result["awarded_marks"],
                final_marks,
                result["confidence"],
                1 if result["needs_review"] else 0,
                result["feedback"],
                json.dumps(result["breakdown"]),
            ),
        )

    total_score = round(obj_score + subj_score, 2)
    pct = round((total_score / max_score * 100.0) if max_score > 0 else 0.0, 2)
    grade = compute_grade_letter(pct)
    passed = 1 if pct >= float(exam["passing_percentage"]) else 0

    logs = [
        dict(r)
        for r in conn.execute(
            "SELECT event_type, severity FROM proctor_logs WHERE attempt_id = ?",
            (attempt_id,),
        ).fetchall()
    ]
    integrity = compute_integrity_summary(logs, strictness=exam["proctoring_strictness"])

    new_status = "PUBLISHED" if (auto_publish or att["status"] == "PUBLISHED") else "EVALUATED"
    conn.execute(
        """
        UPDATE exam_attempts
        SET status = ?, evaluated_at = COALESCE(evaluated_at, datetime('now')),
            objective_score = ?, subjective_score = ?, total_score = ?, max_score = ?,
            percentage = ?, grade = ?, passed = ?, integrity_score = ?, risk_level = ?,
            warning_count = ?
        WHERE id = ?
        """,
        (
            new_status,
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
    conn.commit()
    return get_attempt_detail(conn, attempt_id, include_model_answers=True)


def record_proctor_telemetry(
    conn: sqlite3.Connection,
    attempt_id: int,
    student_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Process webcam CV telemetry or browser integrity event during an exam."""
    att = conn.execute("SELECT * FROM exam_attempts WHERE id = ?", (attempt_id,)).fetchone()
    if not att or att["student_id"] != student_id:
        raise ServiceError("Attempt not found.", status_code=404)
    if att["status"] != "IN_PROGRESS":
        return {"ignored": True, "reason": "Attempt is no longer in progress."}

    exam = conn.execute(
        "SELECT proctoring_strictness, max_warnings, auto_submit_on_warning_limit FROM exams WHERE id = ?",
        (att["exam_id"],),
    ).fetchone()
    strictness = exam["proctoring_strictness"] if exam else "MEDIUM"
    max_warnings = int(exam["max_warnings"]) if exam else 5
    auto_submit_limit = bool(exam["auto_submit_on_warning_limit"]) if exam else True

    event_type = (payload.get("event_type") or "").strip().upper()
    snapshot_b64 = payload.get("snapshot_b64")
    metrics = payload.get("metrics") or {}
    details = (payload.get("details") or "").strip()

    logged_events: list[dict[str, Any]] = []

    if event_type == "CV_FRAME" or (not event_type and metrics):
        cv_result = evaluate_cv_telemetry(metrics, snapshot_b64=snapshot_b64)
        for ev in cv_result["detected_events"]:
            snap_url = save_snapshot_if_flagged(attempt_id, ev["event_type"], snapshot_b64)
            conn.execute(
                """
                INSERT INTO proctor_logs (attempt_id, event_type, severity, details, snapshot_url, metrics_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    ev["event_type"],
                    ev["severity"],
                    ev["details"],
                    snap_url,
                    json.dumps(cv_result),
                ),
            )
            logged_events.append(ev)
    elif event_type and event_type != "HEARTBEAT_OK":
        if event_type not in SEVERITY_BY_EVENT:
            raise ServiceError("Unsupported proctoring event.")
        severity = SEVERITY_BY_EVENT[event_type]
        snap_url = save_snapshot_if_flagged(attempt_id, event_type, snapshot_b64)
        conn.execute(
            """
            INSERT INTO proctor_logs (attempt_id, event_type, severity, details, snapshot_url, metrics_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                event_type,
                severity,
                details or f"Detected {event_type.replace('_', ' ').lower()}.",
                snap_url,
                json.dumps(metrics),
            ),
        )
        logged_events.append({"event_type": event_type, "severity": severity, "details": details})

    all_logs = [
        dict(r)
        for r in conn.execute(
            "SELECT event_type, severity FROM proctor_logs WHERE attempt_id = ?",
            (attempt_id,),
        ).fetchall()
    ]
    integrity = compute_integrity_summary(all_logs, strictness=strictness)
    warning_count = int(integrity["warning_count"])
    warning_limit_reached = warning_count >= max_warnings
    integrity["max_warnings"] = max_warnings
    integrity["warning_limit_reached"] = warning_limit_reached

    conn.execute(
        "UPDATE exam_attempts SET integrity_score = ?, risk_level = ?, warning_count = ? WHERE id = ?",
        (integrity["integrity_score"], integrity["risk_level"], warning_count, attempt_id),
    )
    conn.commit()

    auto_submitted_detail = None
    if warning_limit_reached and auto_submit_limit:
        reason = f"Auto-submitted: reached maximum proctoring warning limit ({warning_count}/{max_warnings})."
        conn.execute(
            """
            UPDATE exam_attempts
            SET status = 'SUBMITTED', submitted_at = datetime('now'),
                termination_reason = ?, faculty_remarks = ?
            WHERE id = ?
            """,
            (reason, reason, attempt_id),
        )
        conn.execute(
            """
            INSERT INTO proctor_logs (attempt_id, event_type, severity, details)
            VALUES (?, 'EXAM_AUTO_TERMINATED', 'HIGH', ?)
            """,
            (attempt_id, reason),
        )
        conn.commit()
        auto_submitted_detail = run_ai_evaluation_for_attempt(conn, attempt_id, auto_publish=True)

    return {
        "logged_count": len(logged_events),
        "logged_events": logged_events,
        "integrity": integrity,
        "auto_submitted": auto_submitted_detail is not None,
        "attempt_detail": auto_submitted_detail,
    }


def list_attempts(
    conn: sqlite3.Connection,
    user: dict[str, Any],
    exam_id: int | None = None,
) -> list[dict[str, Any]]:
    """List exam attempts visible to the current user."""
    params: list[Any] = []
    clauses: list[str] = []

    if user["role"] == "STUDENT":
        clauses.append("a.student_id = ?")
        params.append(user["uid"])
    if exam_id is not None:
        clauses.append("a.exam_id = ?")
        params.append(exam_id)

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"""
        SELECT a.*, e.title AS exam_title, e.subject AS exam_subject, e.passing_percentage,
               u.full_name AS student_name, u.email AS student_email, u.enrollment_no,
               (SELECT COUNT(*) FROM answers ans WHERE ans.attempt_id = a.id AND ans.needs_review = 1 AND ans.faculty_override = 0) AS review_needed_count,
               (SELECT COUNT(*) FROM proctor_logs p WHERE p.attempt_id = a.id AND p.event_type NOT IN ('EXAM_STARTED', 'EXAM_SUBMITTED', 'HEARTBEAT_OK')) AS violation_count
        FROM exam_attempts a
        JOIN exams e ON e.id = a.exam_id
        JOIN users u ON u.id = a.student_id
        {where_sql}
        ORDER BY a.id DESC
        """,
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def get_attempt_detail(
    conn: sqlite3.Connection, attempt_id: int, include_model_answers: bool = True
) -> dict[str, Any]:
    att = conn.execute(
        """
        SELECT a.*, e.title AS exam_title, e.subject AS exam_subject, e.passing_percentage,
               e.proctoring_strictness, u.full_name AS student_name, u.email AS student_email,
               u.enrollment_no, u.department
        FROM exam_attempts a
        JOIN exams e ON e.id = a.exam_id
        JOIN users u ON u.id = a.student_id
        WHERE a.id = ?
        """,
        (attempt_id,),
    ).fetchone()
    if not att:
        raise ServiceError("Attempt not found.", status_code=404)

    q_ans_rows = conn.execute(
        """
        SELECT q.id AS question_id, q.order_index, q.question_type, q.prompt, q.options_json,
               q.model_answer, q.keywords_json, q.max_marks,
               ans.id AS answer_id, ans.student_answer, ans.ai_marks, ans.final_marks,
               ans.ai_confidence, ans.needs_review, ans.ai_feedback, ans.ai_breakdown_json,
               ans.faculty_override, ans.faculty_comment
        FROM questions q
        LEFT JOIN answers ans ON ans.question_id = q.id AND ans.attempt_id = ?
        WHERE q.exam_id = ?
        ORDER BY q.order_index, q.id
        """,
        (attempt_id, att["exam_id"]),
    ).fetchall()

    items: list[dict[str, Any]] = []
    for r in q_ans_rows:
        item: dict[str, Any] = {
            "answer_id": r["answer_id"],
            "question_id": r["question_id"],
            "order_index": r["order_index"],
            "question_type": r["question_type"],
            "prompt": r["prompt"],
            "options": json.loads(r["options_json"]),
            "max_marks": r["max_marks"],
            "student_answer": r["student_answer"] or "",
            "ai_marks": r["ai_marks"] if r["ai_marks"] is not None else 0.0,
            "final_marks": r["final_marks"] if r["final_marks"] is not None else 0.0,
            "ai_confidence": r["ai_confidence"] if r["ai_confidence"] is not None else 1.0,
            "needs_review": bool(r["needs_review"]),
            "ai_feedback": r["ai_feedback"] or "",
            "ai_breakdown": json.loads(r["ai_breakdown_json"] or "{}"),
            "faculty_override": bool(r["faculty_override"]),
            "faculty_comment": r["faculty_comment"] or "",
        }
        if include_model_answers:
            item["model_answer"] = r["model_answer"]
            item["keywords"] = json.loads(r["keywords_json"])
        items.append(item)

    logs = [
        dict(l)
        for l in conn.execute(
            "SELECT * FROM proctor_logs WHERE attempt_id = ? ORDER BY id DESC",
            (attempt_id,),
        ).fetchall()
    ]
    integrity = compute_integrity_summary(logs, strictness=att["proctoring_strictness"])

    return {
        "attempt": dict(att),
        "answers": items,
        "proctor_logs": logs,
        "integrity": integrity,
    }


def override_answer_marks(
    conn: sqlite3.Connection,
    actor_id: int,
    attempt_id: int,
    question_id: int,
    new_marks: float,
    faculty_comment: str = "",
) -> dict[str, Any]:
    """Allow faculty to override AI-awarded marks and recalculate attempt totals."""
    att = conn.execute("SELECT * FROM exam_attempts WHERE id = ?", (attempt_id,)).fetchone()
    if not att:
        raise ServiceError("Attempt not found.", status_code=404)

    q = conn.execute(
        "SELECT * FROM questions WHERE id = ? AND exam_id = ?",
        (question_id, att["exam_id"]),
    ).fetchone()
    if not q:
        raise ServiceError("Question not found for this attempt.", status_code=404)

    if new_marks < 0 or new_marks > float(q["max_marks"]):
        raise ServiceError(f"Marks must be between 0 and {q['max_marks']}.")

    conn.execute(
        """
        UPDATE answers
        SET final_marks = ?, faculty_override = 1, needs_review = 0, faculty_comment = ?
        WHERE attempt_id = ? AND question_id = ?
        """,
        (round(float(new_marks), 2), (faculty_comment or "").strip(), attempt_id, question_id),
    )

    _recalculate_attempt_totals(conn, attempt_id)
    _log_audit(
        conn,
        actor_id,
        "MARKS_OVERRIDDEN",
        "ATTEMPT",
        attempt_id,
        f"Question {question_id} overridden to {new_marks}/{q['max_marks']}.",
    )
    conn.commit()
    return get_attempt_detail(conn, attempt_id, include_model_answers=True)


def _recalculate_attempt_totals(conn: sqlite3.Connection, attempt_id: int) -> None:
    att = conn.execute("SELECT * FROM exam_attempts WHERE id = ?", (attempt_id,)).fetchone()
    exam = conn.execute("SELECT passing_percentage FROM exams WHERE id = ?", (att["exam_id"],)).fetchone()
    rows = conn.execute(
        """
        SELECT q.question_type, q.max_marks, COALESCE(a.final_marks, 0) AS final_marks
        FROM questions q
        LEFT JOIN answers a ON a.question_id = q.id AND a.attempt_id = ?
        WHERE q.exam_id = ?
        """,
        (attempt_id, att["exam_id"]),
    ).fetchall()

    obj_score = 0.0
    subj_score = 0.0
    max_score = 0.0
    for r in rows:
        max_score += float(r["max_marks"])
        if r["question_type"] in ("MCQ", "TRUE_FALSE"):
            obj_score += float(r["final_marks"])
        else:
            subj_score += float(r["final_marks"])

    total_score = round(obj_score + subj_score, 2)
    pct = round((total_score / max_score * 100.0) if max_score > 0 else 0.0, 2)
    grade = compute_grade_letter(pct)
    passed = 1 if pct >= float(exam["passing_percentage"]) else 0

    conn.execute(
        """
        UPDATE exam_attempts
        SET objective_score = ?, subjective_score = ?, total_score = ?, max_score = ?,
            percentage = ?, grade = ?, passed = ?
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
            attempt_id,
        ),
    )


def publish_attempt_result(
    conn: sqlite3.Connection, actor_id: int, attempt_id: int, remarks: str = ""
) -> dict[str, Any]:
    att = conn.execute("SELECT * FROM exam_attempts WHERE id = ?", (attempt_id,)).fetchone()
    if not att:
        raise ServiceError("Attempt not found.", status_code=404)
    conn.execute(
        """
        UPDATE exam_attempts
        SET status = 'PUBLISHED', faculty_remarks = COALESCE(NULLIF(?, ''), faculty_remarks)
        WHERE id = ?
        """,
        ((remarks or "").strip(), attempt_id),
    )
    _log_audit(conn, actor_id, "RESULT_PUBLISHED", "ATTEMPT", attempt_id, "Published student grade report.")
    conn.commit()
    return get_attempt_detail(conn, attempt_id, include_model_answers=True)


def get_system_analytics(conn: sqlite3.Connection, exam_id: int | None = None) -> dict[str, Any]:
    """Compute academic performance, evaluation consistency, and proctoring analytics."""
    exam_filter = "WHERE a.exam_id = ?" if exam_id is not None else ""
    params: tuple[Any, ...] = (exam_id,) if exam_id is not None else ()

    attempts = [
        dict(r)
        for r in conn.execute(
            f"""
            SELECT a.*, e.title AS exam_title
            FROM exam_attempts a
            JOIN exams e ON e.id = a.exam_id
            {exam_filter}
            """,
            params,
        ).fetchall()
    ]

    completed = [a for a in attempts if a["status"] in ("SUBMITTED", "EVALUATED", "PUBLISHED")]
    avg_pct = round(sum(a["percentage"] for a in completed) / len(completed), 2) if completed else 0.0
    avg_integrity = (
        round(sum(a["integrity_score"] for a in completed) / len(completed), 1) if completed else 100.0
    )
    pass_rate = (
        round(sum(1 for a in completed if a["passed"]) / len(completed) * 100.0, 1) if completed else 0.0
    )

    # Score distribution buckets
    buckets = {"0-39": 0, "40-59": 0, "60-79": 0, "80-100": 0}
    risk_counts = {"CLEAR": 0, "WATCH": 0, "FLAGGED": 0}
    for a in completed:
        p = a["percentage"]
        if p < 40:
            buckets["0-39"] += 1
        elif p < 60:
            buckets["40-59"] += 1
        elif p < 80:
            buckets["60-79"] += 1
        else:
            buckets["80-100"] += 1
        risk = a.get("risk_level") or "CLEAR"
        risk_counts[risk] = risk_counts.get(risk, 0) + 1

    # Question-wise average performance
    q_filter = "WHERE q.exam_id = ?" if exam_id is not None else ""
    q_rows = conn.execute(
        f"""
        SELECT q.id, q.exam_id, q.order_index, q.question_type, q.prompt, q.max_marks,
               COUNT(ans.id) AS response_count,
               COALESCE(AVG(ans.final_marks), 0) AS avg_marks,
               COALESCE(AVG(ans.ai_confidence), 1.0) AS avg_confidence,
               SUM(CASE WHEN ans.faculty_override = 1 THEN 1 ELSE 0 END) AS override_count
        FROM questions q
        LEFT JOIN answers ans ON ans.question_id = q.id
        {q_filter}
        GROUP BY q.id
        ORDER BY q.exam_id, q.order_index
        """,
        params,
    ).fetchall()

    question_stats = [
        {
            "question_id": r["id"],
            "exam_id": r["exam_id"],
            "order_index": r["order_index"],
            "question_type": r["question_type"],
            "prompt": r["prompt"],
            "max_marks": r["max_marks"],
            "response_count": r["response_count"],
            "avg_marks": round(float(r["avg_marks"]), 2),
            "avg_pct": round(float(r["avg_marks"]) / float(r["max_marks"]) * 100.0, 1) if r["max_marks"] else 0.0,
            "avg_confidence": round(float(r["avg_confidence"]), 3),
            "override_count": r["override_count"] or 0,
        }
        for r in q_rows
    ]

    totals = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM users WHERE role = 'STUDENT') AS total_students,
            (SELECT COUNT(*) FROM users WHERE role = 'FACULTY') AS total_faculty,
            (SELECT COUNT(*) FROM exams) AS total_exams,
            (SELECT COUNT(*) FROM exam_attempts WHERE status != 'IN_PROGRESS') AS total_submissions
        """
    ).fetchone()

    return {
        "counts": dict(totals),
        "completed_count": len(completed),
        "avg_percentage": avg_pct,
        "pass_rate": pass_rate,
        "avg_integrity_score": avg_integrity,
        "score_distribution": buckets,
        "risk_distribution": risk_counts,
        "question_stats": question_stats,
    }


def export_exam_csv(conn: sqlite3.Connection, exam_id: int) -> str:
    """Export an exam's evaluated mark sheet as CSV."""
    exam = conn.execute("SELECT title, subject FROM exams WHERE id = ?", (exam_id,)).fetchone()
    if not exam:
        raise ServiceError("Exam not found.", status_code=404)

    rows = conn.execute(
        """
        SELECT u.enrollment_no, u.full_name, u.email, a.status,
               a.objective_score, a.subjective_score, a.total_score, a.max_score,
               a.percentage, a.grade, a.passed, a.integrity_score, a.risk_level, a.submitted_at
        FROM exam_attempts a
        JOIN users u ON u.id = a.student_id
        WHERE a.exam_id = ?
        ORDER BY a.total_score DESC, u.full_name ASC
        """,
        (exam_id,),
    ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Enrollment No",
        "Student Name",
        "Email",
        "Status",
        "Objective Marks",
        "Subjective Marks",
        "Total Marks",
        "Max Marks",
        "Percentage",
        "Grade",
        "Result",
        "Integrity Score",
        "Proctor Risk",
        "Submitted At",
    ])
    for r in rows:
        writer.writerow([
            r["enrollment_no"],
            r["full_name"],
            r["email"],
            r["status"],
            r["objective_score"],
            r["subjective_score"],
            r["total_score"],
            r["max_score"],
            f"{r['percentage']}%",
            r["grade"],
            "PASS" if r["passed"] else "FAIL",
            f"{r['integrity_score']}%",
            r["risk_level"],
            r["submitted_at"] or "",
        ])
    return buf.getvalue()


def list_audit_logs(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT l.*, u.full_name AS actor_name, u.role AS actor_role
        FROM audit_logs l
        LEFT JOIN users u ON u.id = l.actor_id
        ORDER BY l.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_user(conn, actor_id, user_id):
    if actor_id == user_id:
        raise ServiceError("You cannot delete your own account.")
    conn.execute("BEGIN IMMEDIATE")
    dependencies = ("exam_attempts WHERE student_id", "exams WHERE created_by",
                    "question_bank WHERE created_by")
    if any(conn.execute(f"SELECT 1 FROM {source} = ? LIMIT 1", (user_id,)).fetchone()
           for source in dependencies):
        raise ServiceError("This account has academic records. Disable it to preserve them.", 409)
    if not conn.execute("DELETE FROM users WHERE id = ?", (user_id,)).rowcount:
        raise ServiceError("User not found.", 404)
    _log_audit(conn, actor_id, "USER_DELETED", "USER", user_id)
    conn.commit()


def delete_exam(conn, actor, exam_id):
    conn.execute("BEGIN IMMEDIATE")
    exam = conn.execute("SELECT created_by FROM exams WHERE id = ?", (exam_id,)).fetchone()
    if not exam or (exam["created_by"] != actor["uid"] and actor["role"] != "ADMIN"):
        raise ServiceError("Exam not found.", 404)
    if conn.execute("SELECT 1 FROM exam_attempts WHERE exam_id = ? LIMIT 1", (exam_id,)).fetchone():
        raise ServiceError("This exam has attempts. Archive it to preserve the results.", 409)
    conn.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
    _log_audit(conn, actor["uid"], "EXAM_DELETED", "EXAM", exam_id)
    conn.commit()


def list_subjects(conn):
    return [dict(row) for row in conn.execute("""
        SELECT s.*, u.full_name AS faculty_name FROM subjects s
        LEFT JOIN users u ON u.id = s.faculty_id ORDER BY s.name
    """)]


def change_subject(conn, actor_id, data, subject_id=None, delete=False):
    if delete:
        result = conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    else:
        code = str(data.get("code") or "").strip().upper()
        name = str(data.get("name") or "").strip()
        faculty = data.get("faculty_id")
        if not code or not name:
            raise ServiceError("Subject code and name are required.")
        if faculty is not None and (type(faculty) is not int or not conn.execute(
            "SELECT 1 FROM users WHERE id = ? AND role = 'FACULTY' AND is_active = 1", (faculty,)
        ).fetchone()):
            raise ServiceError("Choose an active faculty member.")
        values = (code, name, str(data.get("description") or "").strip(), faculty)
        try:
            if subject_id is None:
                result = conn.execute(
                    "INSERT INTO subjects (code, name, description, faculty_id) VALUES (?, ?, ?, ?)", values
                )
                subject_id = result.lastrowid
            else:
                result = conn.execute(
                    "UPDATE subjects SET code = ?, name = ?, description = ?, faculty_id = ? WHERE id = ?",
                    (*values, subject_id),
                )
        except sqlite3.IntegrityError:
            raise ServiceError("Subject code already exists.", 409) from None
    if not result.rowcount:
        raise ServiceError("Subject not found.", 404)
    _log_audit(conn, actor_id, "SUBJECT_DELETED" if delete else "SUBJECT_SAVED", "SUBJECT", subject_id)
    conn.commit()
    return subject_id


def exam_assignments(conn, exam_id):
    exam = conn.execute("SELECT id, title, restricted FROM exams WHERE id = ?", (exam_id,)).fetchone()
    if not exam:
        raise ServiceError("Exam not found.", 404)
    rows = conn.execute("SELECT student_id, due_at FROM exam_assignments WHERE exam_id = ?", (exam_id,))
    return {"exam": dict(exam), "assignments": [dict(row) for row in rows]}


def set_exam_assignments(conn, actor_id, exam_id, data):
    conn.execute("BEGIN IMMEDIATE")
    exam_assignments(conn, exam_id)
    students = data.get("student_ids")
    restricted = data.get("restricted", True)
    if type(restricted) is not bool or not isinstance(students, list) or any(type(i) is not int for i in students):
        raise ServiceError("Invalid assignment settings.")
    active = {row[0] for row in conn.execute("SELECT id FROM users WHERE role = 'STUDENT' AND is_active = 1")}
    if not set(students) <= active:
        raise ServiceError("Select active students only.")
    _, due = _schedule({"closes_at": data.get("due_at")})
    conn.execute("UPDATE exams SET restricted = ? WHERE id = ?", (int(restricted), exam_id))
    conn.execute("DELETE FROM exam_assignments WHERE exam_id = ?", (exam_id,))
    conn.executemany(
        "INSERT INTO exam_assignments (exam_id, student_id, assigned_by, due_at) VALUES (?, ?, ?, ?)",
        [(exam_id, student, actor_id, due) for student in set(students)],
    )
    _log_audit(conn, actor_id, "EXAM_ASSIGNMENTS_UPDATED", "EXAM", exam_id)
    conn.commit()
    return exam_assignments(conn, exam_id)
