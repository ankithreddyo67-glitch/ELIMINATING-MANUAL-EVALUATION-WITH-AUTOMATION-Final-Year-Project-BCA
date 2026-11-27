import { apiFetch, escapeHtml, formatBadge } from "./api.js";
import { renderFacultyAttemptInspector } from "./faculty-attempt.js";

export async function renderSubmissionsTab(container, user) {
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
