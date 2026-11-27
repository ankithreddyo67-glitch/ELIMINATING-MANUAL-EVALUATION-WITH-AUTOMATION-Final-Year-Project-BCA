// Faculty Portal: Evaluation Review & Override, Exam Builder, NLP Sandbox, Analytics

import { apiFetch, escapeHtml, formatBadge, getToken, showToast } from "/js/api.js";
import { createExamDialog, editDraftPaper, editExamSchedule, renderQuestionBank, showExamPaper } from "/js/question-bank.js";
import { renderBarChartSvg, renderRiskBreakdownHtml } from "/js/charts.js";

export async function renderFacultyPortal(container, user, activeTab = "submissions") {
  if (activeTab === "exams") {
    await renderFacultyExamsTab(container, user);
    return;
  }
  if (activeTab === "nlp-sandbox") {
    renderNlpSandboxTab(container);
    return;
  }
  if (activeTab === "analytics") {
    await renderAnalyticsTab(container);
    return;
  }
  await renderSubmissionsTab(container, user);
}

async function renderSubmissionsTab(container, user) {
  container.innerHTML = `<div class="card">Loading submissions &amp; AI evaluations...</div>`;
  const [examsRes, attemptsRes] = await Promise.all([
    apiFetch("/api/exams"),
    apiFetch("/api/attempts"),
  ]);
  const exams = examsRes.exams || [];
  let attempts = attemptsRes.attempts || [];
  let filterExamId = "";

  function draw() {
    const filtered = filterExamId
      ? attempts.filter((a) => String(a.exam_id) === String(filterExamId))
      : attempts;
    const completed = filtered.filter((a) => a.status !== "IN_PROGRESS");
    const needReview = filtered.reduce((s, a) => s + Number(a.review_needed_count || 0), 0);
    const flagged = filtered.filter((a) => a.risk_level === "FLAGGED").length;

    container.innerHTML = `
      <div class="topbar">
        <div>
          <h1 class="page-title">Faculty Evaluation &amp; Proctoring Console</h1>
          <p class="page-sub">Audit AI-graded subjective answers, inspect proctoring flags, override marks, and publish results.</p>
        </div>
        <div style="display:flex;gap:10px;align-items:center;">
          <select id="exam-filter" style="width:260px;">
            <option value="">All Examinations</option>
            ${exams.map((e) => `<option value="${e.id}" ${String(filterExamId) === String(e.id) ? "selected" : ""}>${escapeHtml(e.title)}</option>`).join("")}
          </select>
        </div>
      </div>

      <div class="grid grid-4" style="margin-bottom:20px;">
        <div class="card kpi-card">
          <span class="kpi-label">Total Submissions</span>
          <span class="kpi-value">${completed.length}</span>
          <span class="kpi-foot">Automated &amp; ready for audit</span>
        </div>
        <div class="card kpi-card">
          <span class="kpi-label">Low-Confidence Answers</span>
          <span class="kpi-value">${needReview}</span>
          <span class="kpi-foot">Flagged by NLP confidence estimator</span>
        </div>
        <div class="card kpi-card">
          <span class="kpi-label">Proctoring Flagged</span>
          <span class="kpi-value">${flagged}</span>
          <span class="kpi-foot">High-severity or low integrity</span>
        </div>
        <div class="card kpi-card">
          <span class="kpi-label">Published Results</span>
          <span class="kpi-value">${filtered.filter((a) => a.status === "PUBLISHED").length}</span>
          <span class="kpi-foot">Visible to students</span>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Student Examination Attempts</h3>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Student</th>
                <th>Exam</th>
                <th>Status</th>
                <th>Obj / Subj</th>
                <th>Total (%)</th>
                <th>Integrity</th>
                <th>Review Flags</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${
                filtered.length === 0
                  ? `<tr><td colspan="8" style="color:var(--text-muted);">No attempts found.</td></tr>`
                  : filtered
                      .map(
                        (a) => `
                  <tr>
                    <td>
                      <strong>${escapeHtml(a.student_name)}</strong>
                      <div style="font-size:0.76rem;color:var(--text-muted);">${escapeHtml(a.enrollment_no || a.student_email)}</div>
                    </td>
                    <td>${escapeHtml(a.exam_title)}</td>
                    <td><span class="badge ${formatBadge(a.status)}">${escapeHtml(a.status)}</span></td>
                    <td>${a.objective_score} / ${a.subjective_score}</td>
                    <td><strong>${a.total_score}/${a.max_score}</strong> (${a.percentage}% • ${escapeHtml(a.grade)})</td>
                    <td>
                      <span class="badge ${formatBadge(a.risk_level)}">${a.integrity_score}% ${escapeHtml(a.risk_level)}</span>
                      <div style="font-size:0.75rem;color:var(--text-muted);">${a.violation_count} events</div>
                    </td>
                    <td>
                      ${
                        a.review_needed_count > 0
                          ? `<span class="badge badge-warning">${a.review_needed_count} need review</span>`
                          : `<span class="badge badge-success">High confidence</span>`
                      }
                    </td>
                    <td>
                      <button class="btn btn-sm btn-primary inspect-attempt" data-id="${a.id}">Inspect &amp; Grade</button>
                    </td>
                  </tr>
                `
                      )
                      .join("")
              }
            </tbody>
          </table>
        </div>
      </div>
    `;

    container.querySelector("#exam-filter").onchange = (e) => {
      filterExamId = e.target.value;
      draw();
    };
    container.querySelectorAll(".inspect-attempt").forEach((btn) => {
      btn.onclick = () => renderFacultyAttemptInspector(container, user, Number(btn.dataset.id));
    });
  }

  draw();
}

async function renderFacultyAttemptInspector(container, user, attemptId) {
  container.innerHTML = `<div class="card">Loading attempt details...</div>`;
  const data = await apiFetch(`/api/attempts/${attemptId}`);
  const { attempt, answers, proctor_logs } = data;

  container.innerHTML = `
    <div class="topbar">
      <div>
        <h1 class="page-title">Evaluation &amp; Proctoring Audit</h1>
        <p class="page-sub">${escapeHtml(attempt.student_name)} (${escapeHtml(attempt.enrollment_no || attempt.student_email)}) • ${escapeHtml(attempt.exam_title)}</p>
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;">
        <button class="btn" id="back-submissions">Back to Submissions</button>
        <button class="btn" id="rerun-ai-btn">Re-Run AI Evaluator</button>
        <button class="btn btn-success" id="publish-result-btn">${attempt.status === "PUBLISHED" ? "Update Remarks / Published" : "Publish Result"}</button>
      </div>
    </div>

    <div class="grid grid-4" style="margin-bottom:20px;">
      <div class="card kpi-card">
        <span class="kpi-label">Total Score</span>
        <span class="kpi-value">${attempt.total_score} / ${attempt.max_score}</span>
        <span class="kpi-foot">${attempt.percentage}% • Grade ${escapeHtml(attempt.grade)}</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Objective / Subjective</span>
        <span class="kpi-value">${attempt.objective_score} / ${attempt.subjective_score}</span>
        <span class="kpi-foot">${attempt.passed ? "PASS" : "FAIL"}</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Integrity Score</span>
        <span class="kpi-value">${attempt.integrity_score}%</span>
        <span class="kpi-foot"><span class="badge ${formatBadge(attempt.risk_level)}">${escapeHtml(attempt.risk_level)}</span></span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Faculty Remarks</span>
        <input id="faculty-remarks-input" type="text" value="${escapeHtml(attempt.faculty_remarks || "")}" placeholder="Optional summary note..." />
      </div>
    </div>

    <div class="grid" style="gap:16px;">
      ${answers
        .map((a) => {
          const bd = a.ai_breakdown || {};
          return `
            <div class="card">
              <div class="card-header">
                <div>
                  <span class="badge badge-primary">Q${a.order_index} • ${escapeHtml(a.question_type)}</span>
                  <span class="badge ${a.needs_review ? "badge-warning" : "badge-success"}">
                    AI Confidence: ${Math.round((a.ai_confidence || 0) * 100)}%
                  </span>
                  ${a.faculty_override ? `<span class="badge badge-warning">Overridden</span>` : ""}
                  <h4 style="margin:8px 0 0;">${escapeHtml(a.prompt)}</h4>
                </div>
                <div style="text-align:right;">
                  <div style="font-size:1.2rem;font-weight:750;">Final: ${a.final_marks} / ${a.max_marks}</div>
                  <div style="font-size:0.78rem;color:var(--text-muted);">AI Predicted: ${a.ai_marks}</div>
                </div>
              </div>

              <div class="grid grid-2" style="margin-bottom:12px;">
                <div style="background:var(--bg);padding:12px;border-radius:9px;border:1px solid var(--border);">
                  <div style="font-size:0.74rem;font-weight:700;color:var(--text-muted);margin-bottom:4px;">STUDENT ANSWER</div>
                  <div style="font-size:0.88rem;">${escapeHtml(a.student_answer || "(Blank)")}</div>
                </div>
                <div style="background:var(--bg);padding:12px;border-radius:9px;border:1px solid var(--border);">
                  <div style="font-size:0.74rem;font-weight:700;color:var(--text-muted);margin-bottom:4px;">MODEL ANSWER</div>
                  <div style="font-size:0.88rem;">${escapeHtml(a.model_answer || "")}</div>
                </div>
              </div>

              <div style="font-size:0.85rem;margin-bottom:8px;">
                <strong>AI Explanation:</strong> ${escapeHtml(a.ai_feedback)}
              </div>

              ${
                !["MCQ", "TRUE_FALSE", "PROGRAMMING"].includes(a.question_type)
                  ? `
                <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:0.8rem;color:var(--text-muted);margin-bottom:10px;">
                  <span>TF-IDF Cosine: <strong>${Math.round((bd.tfidf_cosine || 0) * 100)}%</strong></span>
                  ${bd.bm25_similarity !== undefined ? `<span>BM25: <strong>${Math.round(bd.bm25_similarity * 100)}%</strong></span>` : ""}
                  ${bd.bigram_f1 !== undefined ? `<span>Bigram F1: <strong>${Math.round(bd.bigram_f1 * 100)}%</strong></span>` : ""}
                  <span>Concept Coverage: <strong>${Math.round((bd.concept_coverage || 0) * 100)}%</strong></span>
                </div>
                <div class="tag-list" style="margin-bottom:12px;">
                  ${(bd.matched_concepts || []).map((c) => `<span class="tag tag-hit">+ ${escapeHtml(c)}</span>`).join("")}
                  ${(bd.missing_concepts || []).map((c) => `<span class="tag tag-miss">- ${escapeHtml(c)}</span>`).join("")}
                </div>
              `
                  : ""
              }

              <form class="override-form" data-qid="${a.question_id}" style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;padding-top:10px;border-top:1px solid var(--border);">
                <div style="width:130px;">
                  <label>Override Marks (0–${a.max_marks})</label>
                  <input type="number" step="0.25" min="0" max="${a.max_marks}" name="marks" value="${a.final_marks}" required />
                </div>
                <div style="flex:1;min-width:220px;">
                  <label>Faculty Comment</label>
                  <input type="text" name="comment" value="${escapeHtml(a.faculty_comment || "")}" placeholder="Reason for grade adjustment or confirmation..." />
                </div>
                <button type="submit" class="btn btn-sm btn-primary">Save Marks</button>
              </form>
            </div>
          `;
        })
        .join("")}
    </div>

    <div class="card" style="margin-top:20px;">
      <h3 class="card-title" style="margin-bottom:10px;">Proctoring Violation Timeline &amp; Evidence</h3>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Event</th><th>Severity</th><th>Details</th><th>Snapshot</th><th>Time</th></tr></thead>
          <tbody>
            ${proctor_logs
              .map(
                (l) => `
              <tr>
                <td><strong>${escapeHtml(l.event_type)}</strong></td>
                <td><span class="badge ${formatBadge(l.severity)}">${escapeHtml(l.severity)}</span></td>
                <td>${escapeHtml(l.details)}</td>
                <td>${l.snapshot_url ? `<button class="btn btn-ghost btn-sm" data-snapshot="${escapeHtml(l.snapshot_url)}">View capture</button>` : "—"}</td>
                <td style="font-size:0.78rem;color:var(--text-muted);">${escapeHtml(l.created_at)}</td>
              </tr>
            `
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;

  container.querySelectorAll("[data-snapshot]").forEach((button) => {
    button.onclick = async () => {
      button.disabled = true;
      try {
        const response = await apiFetch(button.dataset.snapshot, { rawResponse: true });
        const image = document.createElement("img");
        const url = URL.createObjectURL(await response.blob());
        image.className = "snapshot-thumb";
        image.alt = "Proctor capture";
        image.onload = image.onerror = () => URL.revokeObjectURL(url);
        image.src = url;
        button.replaceWith(image);
      } catch (err) {
        button.disabled = false;
        showToast(err.message, "error");
      }
    };
  });

  container.querySelector("#back-submissions").onclick = () => renderSubmissionsTab(container, user);

  container.querySelector("#rerun-ai-btn").onclick = async () => {
    try {
      await apiFetch(`/api/attempts/${attemptId}/evaluate`, { method: "POST", body: {} });
      showToast("AI evaluation re-run completed.", "success");
      renderFacultyAttemptInspector(container, user, attemptId);
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  container.querySelector("#publish-result-btn").onclick = async () => {
    const remarks = container.querySelector("#faculty-remarks-input").value;
    try {
      await apiFetch(`/api/attempts/${attemptId}/publish`, {
        method: "POST",
        body: { faculty_remarks: remarks },
      });
      showToast("Result published to student portal.", "success");
      renderFacultyAttemptInspector(container, user, attemptId);
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  container.querySelectorAll(".override-form").forEach((form) => {
    form.onsubmit = async (e) => {
      e.preventDefault();
      const qid = Number(form.dataset.qid);
      const marks = Number(form.querySelector("input[name='marks']").value);
      const comment = form.querySelector("input[name='comment']").value;
      try {
        await apiFetch(`/api/attempts/${attemptId}/override`, {
          method: "POST",
          body: { question_id: qid, final_marks: marks, faculty_comment: comment },
        });
        showToast("Marks overridden and totals recalculated.", "success");
        renderFacultyAttemptInspector(container, user, attemptId);
      } catch (err) {
        showToast(err.message, "error");
      }
    };
  });
}

async function renderFacultyExamsTab(container, user) {
  container.innerHTML = `<div class="card">Loading examinations...</div>`;
  const data = await apiFetch("/api/exams");
  const exams = data.exams || [];

  container.innerHTML = `
    <div class="topbar">
      <div>
        <h1 class="page-title">Examinations &amp; Question Bank</h1>
        <p class="page-sub">Manage reusable questions, create papers, and schedule exams.</p>
      </div>
      <div class="assessment-actions">
        <button class="btn" id="question-bank-btn">Open question bank</button>
        <button class="btn btn-primary" id="new-exam-btn">Create exam</button>
      </div>
    </div>

    <div class="grid grid-2">
      ${exams
        .map(
          (ex) => `
        <div class="card">
          <div class="card-header">
            <div>
              <span class="badge badge-primary">${escapeHtml(ex.subject)}</span>
              <h3 style="margin:8px 0 4px;">${escapeHtml(ex.title)}</h3>
            </div>
            <span class="badge ${formatBadge(ex.status)}">${escapeHtml(ex.status)}</span>
          </div>
          <p style="font-size:0.86rem;color:var(--text-muted);margin:0 0 12px;">${escapeHtml(ex.description)}</p>
          <div style="display:flex;gap:14px;flex-wrap:wrap;font-size:0.82rem;color:var(--text-muted);margin-bottom:14px;">
            <span>Questions: <strong>${ex.question_count}</strong></span>
            <span>Marks: <strong>${ex.total_marks}</strong></span>
            <span>Duration: <strong>${ex.duration_minutes}m</strong></span>
            ${ex.opens_at ? `<span>Opens: <strong>${escapeHtml(new Date(ex.opens_at).toLocaleString())}</strong></span>` : ""}
            ${ex.closes_at ? `<span>Last start: <strong>${escapeHtml(new Date(ex.closes_at).toLocaleString())}</strong></span>` : ""}
            <span>Attempts: <strong>${ex.attempt_count ?? 0}</strong></span>
            <span>Proctoring: <strong>${ex.proctoring_strictness}</strong></span>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <button class="btn btn-sm" data-paper="${ex.id}">View paper</button>
            ${ex.status === "DRAFT" && !ex.attempt_count && (user.role === "ADMIN" || ex.created_by === user.id)
              ? `<button class="btn btn-sm" data-edit-paper="${ex.id}">Edit paper</button>` : ""}
            ${user.role === "ADMIN" || ex.created_by === user.id
              ? `<button class="btn btn-sm" data-schedule="${ex.id}">Edit schedule</button>` : ""}
            ${!ex.attempt_count && (user.role === "ADMIN" || ex.created_by === user.id)
              ? `<button class="btn btn-sm btn-danger" data-delete-exam="${ex.id}">Delete exam</button>` : ""}
            <button class="btn btn-sm export-csv-btn" data-id="${ex.id}">Export CSV Results</button>
            <button class="btn btn-sm toggle-status-btn" data-id="${ex.id}" data-next="${ex.status === "PUBLISHED" ? "ARCHIVED" : "PUBLISHED"}">
              ${ex.status === "PUBLISHED" ? "Archive" : "Publish"}
            </button>
          </div>
        </div>
      `
        )
        .join("")}
    </div>
  `;

  const refresh = () => renderFacultyExamsTab(container, user);
  const reportError = (error) => showToast(error.message, "error");
  container.querySelector("#new-exam-btn").onclick = () => createExamDialog(refresh).catch(reportError);
  container.querySelector("#question-bank-btn").onclick = () => renderQuestionBank(container, refresh).catch(reportError);
  container.querySelectorAll("[data-delete-exam]").forEach((button) => {
    button.onclick = async () => {
      if (!window.confirm("Delete this exam?")) return;
      try {
        await apiFetch(`/api/exams/${button.dataset.deleteExam}`, { method: "DELETE" });
        await refresh();
      } catch (error) {
        reportError(error);
      }
    };
  });
  container.querySelectorAll("[data-edit-paper]").forEach((button) => {
    button.onclick = () => editDraftPaper(button.dataset.editPaper, refresh).catch(reportError);
  });
  container.querySelectorAll("[data-paper]").forEach((button) => {
    button.onclick = () => showExamPaper(button.dataset.paper).catch(reportError);
  });
  container.querySelectorAll("[data-schedule]").forEach((button) => {
    button.onclick = () => editExamSchedule(exams.find((exam) => exam.id === Number(button.dataset.schedule)), refresh);
  });

  container.querySelectorAll(".toggle-status-btn").forEach((btn) => {
    btn.onclick = async () => {
      try {
        await apiFetch(`/api/exams/${btn.dataset.id}/status`, {
          method: "PATCH",
          body: { status: btn.dataset.next },
        });
        showToast(`Exam status updated to ${btn.dataset.next}.`, "success");
        renderFacultyExamsTab(container, user);
      } catch (err) {
        showToast(err.message, "error");
      }
    };
  });

  container.querySelectorAll(".export-csv-btn").forEach((btn) => {
    btn.onclick = async () => {
      try {
        const res = await fetch(`/api/exams/${btn.dataset.id}/export`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        });
        if (!res.ok) throw new Error("Export failed");
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `exam_${btn.dataset.id}_results.csv`;
        a.click();
        URL.revokeObjectURL(url);
        showToast("CSV mark sheet downloaded.", "success");
      } catch (err) {
        showToast(err.message, "error");
      }
    };
  });
}

function renderNlpSandboxTab(container) {
  container.innerHTML = `
    <div class="topbar">
      <div>
        <h1 class="page-title">Live AI Subjective Grading Sandbox</h1>
        <p class="page-sub">Test the ML/NLP evaluation ensemble (TF-IDF Cosine, BM25, Bigram F1, Rubric Coverage, Negation Guard).</p>
      </div>
    </div>

    <div class="grid grid-2">
      <div class="card">
        <form id="nlp-sandbox-form">
          <div class="grid grid-2">
            <div class="form-group">
              <label>Question Type</label>
              <select id="sb-type">
                <option value="SUBJECTIVE" selected>SUBJECTIVE</option>
                <option value="SHORT">SHORT</option>
              </select>
            </div>
            <div class="form-group">
              <label>Max Marks</label>
              <input id="sb-marks" type="number" value="10" min="1" step="0.5" />
            </div>
          </div>
          <div class="form-group">
            <label>Reference / Model Answer</label>
            <textarea id="sb-model" rows="4">Gradient descent is an iterative optimization algorithm used to minimize a loss function by updating model parameters in the opposite direction of the gradient scaled by the learning rate.</textarea>
          </div>
          <div class="form-group">
            <label>Rubric Key Concepts (comma-separated)</label>
            <input id="sb-keywords" value="iterative optimization, loss function, parameters, gradient, learning rate" />
          </div>
          <div class="form-group">
            <label>Sample Student Answer</label>
            <textarea id="sb-student" rows="4">Gradient descent minimizes the loss function iteratively by adjusting weights using the learning rate along the negative gradient.</textarea>
          </div>
          <button type="submit" class="btn btn-primary">Evaluate with ML/NLP Engine</button>
        </form>
      </div>

      <div class="card" id="sb-output">
        <h3 class="card-title">Evaluation Breakdown</h3>
        <p style="color:var(--text-muted);font-size:0.88rem;">Click "Evaluate with ML/NLP Engine" to inspect similarity signals, concept coverage, confidence, and feedback.</p>
      </div>
    </div>
  `;

  async function runPreview() {
    const out = container.querySelector("#sb-output");
    try {
      const res = await apiFetch("/api/nlp/preview", {
        method: "POST",
        body: {
          question_type: container.querySelector("#sb-type").value,
          max_marks: Number(container.querySelector("#sb-marks").value),
          model_answer: container.querySelector("#sb-model").value,
          keywords: container.querySelector("#sb-keywords").value,
          student_answer: container.querySelector("#sb-student").value,
        },
      });
      const ev = res.evaluation;
      const bd = ev.breakdown || {};
      out.innerHTML = `
        <div class="card-header">
          <h3 class="card-title">Evaluation Breakdown</h3>
          <span class="badge ${ev.needs_review ? "badge-warning" : "badge-success"}">
            Confidence: ${Math.round(ev.confidence * 100)}%
          </span>
        </div>
        <div style="font-size:2rem;font-weight:800;margin-bottom:10px;">
          ${ev.awarded_marks} <span style="font-size:1rem;color:var(--text-muted);">/ ${ev.max_marks} marks</span>
        </div>
        <p style="font-size:0.9rem;margin-bottom:16px;">${escapeHtml(ev.feedback)}</p>

        ${[
          ["Concept Coverage", bd.concept_coverage],
          ["TF-IDF Cosine Similarity", bd.tfidf_cosine],
          ["BM25 Term Relevance", bd.bm25_similarity],
          ["Bigram Phrase F1", bd.bigram_f1],
          ["Length Adequacy", bd.length_adequacy],
        ]
          .filter(([, val]) => val !== undefined)
          .map(
            ([label, val]) => `
          <div style="margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:3px;">
              <span>${label}</span><strong>${Math.round(val * 100)}%</strong>
            </div>
            <div class="meter"><div class="meter-fill" style="width:${Math.round(val * 100)}%"></div></div>
          </div>
        `
          )
          .join("")}

        <div style="margin-top:14px;">
          <div style="font-size:0.78rem;color:var(--text-muted);margin-bottom:6px;">Rubric Concepts</div>
          <div class="tag-list">
            ${(bd.matched_concepts || []).map((c) => `<span class="tag tag-hit">+ ${escapeHtml(c)}</span>`).join("")}
            ${(bd.missing_concepts || []).map((c) => `<span class="tag tag-miss">- ${escapeHtml(c)}</span>`).join("")}
          </div>
        </div>
      `;
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  container.querySelector("#nlp-sandbox-form").onsubmit = (e) => {
    e.preventDefault();
    runPreview();
  };
  runPreview();
}

export async function renderAnalyticsTab(container) {
  container.innerHTML = `<div class="card">Loading analytics...</div>`;
  const data = await apiFetch("/api/analytics");
  const dist = data.score_distribution || {};

  const scoreChart = renderBarChartSvg([
    { label: "0–39%", value: dist["0-39"] || 0, color: "#ef4444" },
    { label: "40–59%", value: dist["40-59"] || 0, color: "#f59e0b" },
    { label: "60–79%", value: dist["60-79"] || 0, color: "#06b6d4" },
    { label: "80–100%", value: dist["80-100"] || 0, color: "#10b981" },
  ]);

  container.innerHTML = `
    <div class="topbar">
      <div>
        <h1 class="page-title">Academic &amp; Integrity Analytics</h1>
        <p class="page-sub">Aggregated score distributions, AI confidence consistency, and proctoring integrity telemetry.</p>
      </div>
    </div>

    <div class="grid grid-4" style="margin-bottom:20px;">
      <div class="card kpi-card">
        <span class="kpi-label">Completed Submissions</span>
        <span class="kpi-value">${data.completed_count}</span>
        <span class="kpi-foot">${data.counts.total_exams} active exams</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Mean Score</span>
        <span class="kpi-value">${data.avg_percentage}%</span>
        <span class="kpi-foot">Pass Rate: ${data.pass_rate}%</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Mean Integrity</span>
        <span class="kpi-value">${data.avg_integrity_score}%</span>
        <span class="kpi-foot">Across CV &amp; browser checks</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Registered Students</span>
        <span class="kpi-value">${data.counts.total_students}</span>
        <span class="kpi-foot">${data.counts.total_faculty} faculty members</span>
      </div>
    </div>

    <div class="grid grid-2" style="margin-bottom:20px;">
      <div class="card">
        <h3 class="card-title" style="margin-bottom:10px;">Score Distribution</h3>
        ${scoreChart}
      </div>
      <div class="card">
        <h3 class="card-title" style="margin-bottom:14px;">Proctoring Risk Breakdown</h3>
        ${renderRiskBreakdownHtml(data.risk_distribution || {})}
      </div>
    </div>

    <div class="card">
      <h3 class="card-title" style="margin-bottom:12px;">Question-Wise Performance &amp; AI Calibration</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Type</th>
              <th>Question</th>
              <th>Responses</th>
              <th>Avg Score</th>
              <th>AI Confidence</th>
              <th>Overrides</th>
            </tr>
          </thead>
          <tbody>
            ${(data.question_stats || [])
              .map(
                (q) => `
              <tr>
                <td>Q${q.order_index}</td>
                <td><span class="badge badge-primary">${escapeHtml(q.question_type)}</span></td>
                <td style="max-width:420px;">${escapeHtml(q.prompt)}</td>
                <td>${q.response_count}</td>
                <td><strong>${q.avg_marks} / ${q.max_marks}</strong> (${q.avg_pct}%)</td>
                <td>${Math.round(q.avg_confidence * 100)}%</td>
                <td>${q.override_count}</td>
              </tr>
            `
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}
