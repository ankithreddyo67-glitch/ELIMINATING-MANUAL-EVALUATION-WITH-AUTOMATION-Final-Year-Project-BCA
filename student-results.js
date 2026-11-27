import { apiFetch, escapeHtml, formatBadge } from "./api.js";
import { renderAttemptReportCard } from "./attempt-report.js";

export async function renderStudentResultsList(container, user) {
  container.innerHTML = `<div class="card">Loading your results...</div>`;
  const data = await apiFetch("/api/attempts");
  const attempts = data.attempts || [];

  container.innerHTML = `
    <div class="topbar">
      <div>
        <h1 class="page-title">My Results &amp; AI Evaluations</h1>
        <p class="page-sub">Inspect per-question NLP feedback, matched rubric concepts, and integrity scores.</p>
      </div>
    </div>
    <div class="card">
      ${
        attempts.length === 0
          ? `<p style="color:var(--text-muted);">No examination attempts recorded yet.</p>`
          : `
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Exam</th>
                <th>Status</th>
                <th>Objective</th>
                <th>Subjective (NLP)</th>
                <th>Total</th>
                <th>Grade</th>
                <th>Integrity</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${attempts
                .map(
                  (a) => `
                <tr>
                  <td>
                    <strong>${escapeHtml(a.exam_title)}</strong>
                    <div style="font-size:0.78rem;color:var(--text-muted);">${escapeHtml(a.exam_subject)}</div>
                  </td>
                  <td><span class="badge ${formatBadge(a.status)}">${escapeHtml(a.status)}</span></td>
                  <td>${a.objective_score}</td>
                  <td>${a.subjective_score}</td>
                  <td><strong>${a.total_score}/${a.max_score}</strong> (${a.percentage}%)</td>
                  <td><span class="badge ${a.passed ? "badge-success" : "badge-danger"}">${escapeHtml(a.grade)}</span></td>
                  <td><span class="badge ${formatBadge(a.risk_level)}">${a.integrity_score}% (${escapeHtml(a.risk_level)})</span></td>
                  <td>
                    <button class="btn btn-sm btn-primary open-report" data-id="${a.id}">Report Card</button>
                  </td>
                </tr>
              `
                )
                .join("")}
            </tbody>
          </table>
        </div>
      `
      }
    </div>
  `;

  container.querySelectorAll(".open-report").forEach((btn) => {
    btn.onclick = () => renderAttemptReportCard(container, user, Number(btn.dataset.id));
  });
}
