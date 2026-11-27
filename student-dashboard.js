import { apiFetch, escapeHtml, formatBadge } from "./api.js";
import { openProctorPreflightModal } from "./exam-preflight.js";
import { renderAttemptReportCard } from "./attempt-report.js";

export async function renderStudentDashboard(container, user) {
  container.innerHTML = `<div class="card">Loading examinations...</div>`;
  const [examData, attemptData] = await Promise.all([
    apiFetch("/api/exams"),
    apiFetch("/api/attempts"),
  ]);

  const exams = examData.exams || [];
  const attempts = attemptData.attempts || [];
  const completed = attempts.filter((a) => a.status !== "IN_PROGRESS");
  const avgPct = completed.length
    ? (completed.reduce((s, a) => s + Number(a.percentage || 0), 0) / completed.length).toFixed(1)
    : "—";
  const avgIntegrity = completed.length
    ? (completed.reduce((s, a) => s + Number(a.integrity_score || 100), 0) / completed.length).toFixed(1)
    : "100.0";

  container.innerHTML = `
    <div class="topbar">
      <div>
        <h1 class="page-title">Student Examination Portal</h1>
        <p class="page-sub">Welcome back, ${escapeHtml(user.full_name)} (${escapeHtml(user.enrollment_no || user.department)})</p>
      </div>
    </div>

    <div class="grid grid-4" style="margin-bottom:22px;">
      <div class="card kpi-card">
        <span class="kpi-label">Available Exams</span>
        <span class="kpi-value">${exams.length}</span>
        <span class="kpi-foot">Active published assessments</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Completed</span>
        <span class="kpi-value">${completed.length}</span>
        <span class="kpi-foot">Auto-evaluated submissions</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Average Score</span>
        <span class="kpi-value">${avgPct}${avgPct === "—" ? "" : "%"}</span>
        <span class="kpi-foot">Combined objective &amp; NLP subjective</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Integrity Index</span>
        <span class="kpi-value">${avgIntegrity}%</span>
        <span class="kpi-foot">CV &amp; browser proctoring score</span>
      </div>
    </div>

    <div class="card" style="margin-bottom:22px;">
      <div class="card-header">
        <div>
          <h3 class="card-title">Published Examinations</h3>
          <p class="page-sub">Launch a proctored exam or review your instant AI-graded report card.</p>
        </div>
      </div>
      <div class="grid grid-2">
        ${exams
          .map((ex) => {
            const att = ex.my_attempt;
            const statusText = att ? att.status : "NOT_STARTED";
            let actionBtn = `<button class="btn btn-primary start-exam-btn" data-exam-id="${ex.id}">Start Proctored Exam</button>`;
            if (att && att.status === "IN_PROGRESS") {
              actionBtn = `<button class="btn btn-primary start-exam-btn" data-exam-id="${ex.id}">Resume Exam</button>`;
            } else if (att) {
              actionBtn = `<button class="btn view-report-btn" data-attempt-id="${att.id}">View AI Report Card</button>`;
            }
            if (!att && ex.opens_at && Date.now() < Date.parse(ex.opens_at)) {
              actionBtn = '<span class="badge badge-muted">Scheduled · refresh after opening</span>';
            } else if (!att && [ex.closes_at, ex.assignment_due_at].some((date) => date && Date.now() >= Date.parse(date))) {
              actionBtn = '<span class="badge badge-muted">Start window closed</span>';
            }
            return `
              <div class="card" style="background:var(--bg-soft);box-shadow:none;">
                <div class="card-header">
                  <div>
                    <span class="badge badge-primary">${escapeHtml(ex.subject)}</span>
                    <h4 style="margin:8px 0 4px;">${escapeHtml(ex.title)}</h4>
                  </div>
                  <span class="badge ${formatBadge(statusText)}">${escapeHtml(statusText.replace("_", " "))}</span>
                </div>
                <p style="font-size:0.86rem;color:var(--text-muted);margin:0 0 12px;">${escapeHtml(ex.description)}</p>
                <div style="display:flex;gap:14px;flex-wrap:wrap;font-size:0.82rem;color:var(--text-muted);margin-bottom:14px;">
                  <span>Questions: <strong>${ex.question_count}</strong></span>
                  <span>Total Marks: <strong>${ex.total_marks}</strong></span>
                  ${ex.assignment_due_at ? `<span>Assignment deadline: <strong>${escapeHtml(new Date(ex.assignment_due_at).toLocaleString())}</strong></span>` : ""}
                  <span>Duration: <strong>${ex.duration_minutes} min</strong></span>
                  ${ex.opens_at ? `<span>Opens: <strong>${escapeHtml(new Date(ex.opens_at).toLocaleString())}</strong></span>` : ""}
                  ${ex.closes_at ? `<span>Last start: <strong>${escapeHtml(new Date(ex.closes_at).toLocaleString())}</strong></span>` : ""}
                  <span>Proctoring: <strong>${ex.proctoring_enabled ? ex.proctoring_strictness : "OFF"}</strong></span>
                </div>
                ${
                  att && att.status !== "IN_PROGRESS"
                    ? `<div style="margin-bottom:12px;font-size:0.86rem;">
                         Score: <strong>${att.total_score}/${att.max_score} (${att.percentage}%)</strong> • Grade: <strong>${escapeHtml(att.grade)}</strong> • Integrity: <strong>${att.integrity_score}%</strong>
                       </div>`
                    : ""
                }
                ${actionBtn}
              </div>
            `;
          })
          .join("")}
      </div>
    </div>
  `;

  container.querySelectorAll(".start-exam-btn").forEach((btn) => {
    btn.onclick = () => openProctorPreflightModal(container, user, Number(btn.dataset.examId));
  });
  container.querySelectorAll(".view-report-btn").forEach((btn) => {
    btn.onclick = () => renderAttemptReportCard(container, user, Number(btn.dataset.attemptId));
  });
}
