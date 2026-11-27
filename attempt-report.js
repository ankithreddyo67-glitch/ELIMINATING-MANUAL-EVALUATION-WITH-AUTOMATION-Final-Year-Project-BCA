import { apiFetch, escapeHtml, formatBadge } from "./api.js";
import { renderStudentDashboard } from "./student-dashboard.js";

export async function renderAttemptReportCard(container, user, attemptId, preloaded = null) {
  const data = preloaded || (await apiFetch(`/api/attempts/${attemptId}`));
  const { attempt, answers, proctor_logs } = data;

  container.innerHTML = `
    <div class="topbar no-print">
      <div>
        <h1 class="page-title">Automated Assessment Report Card</h1>
        <p class="page-sub">${escapeHtml(attempt.exam_title)} • ${escapeHtml(attempt.student_name)}</p>
      </div>
      <div style="display:flex;gap:10px;">
        <button class="btn" id="back-student-dash">Back to Dashboard</button>
        <button class="btn btn-primary" id="print-report-btn">Print / Save PDF</button>
      </div>
    </div>

    <div class="card" style="margin-bottom:20px;">
      <div class="grid grid-4">
        <div class="kpi-card">
          <span class="kpi-label">Final Score</span>
          <span class="kpi-value">${attempt.total_score} / ${attempt.max_score}</span>
          <span class="kpi-foot">${attempt.percentage}% (${attempt.passed ? "PASSED" : "FAILED"})</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Grade</span>
          <span class="kpi-value">${escapeHtml(attempt.grade)}</span>
          <span class="kpi-foot">Objective: ${attempt.objective_score} • Subjective: ${attempt.subjective_score}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Proctoring Integrity</span>
          <span class="kpi-value">${attempt.integrity_score}%</span>
          <span class="kpi-foot"><span class="badge ${formatBadge(attempt.risk_level)}">${escapeHtml(attempt.risk_level)}</span></span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Evaluation Status</span>
          <span class="kpi-value" style="font-size:1.25rem;padding-top:6px;">
            <span class="badge ${formatBadge(attempt.status)}">${escapeHtml(attempt.status)}</span>
          </span>
          <span class="kpi-foot">${escapeHtml(attempt.faculty_remarks || "Auto-graded via ML/NLP pipeline")}</span>
        </div>
      </div>
    </div>

    <div class="grid" style="gap:16px;">
      ${answers
        .map((a) => {
          const bd = a.ai_breakdown || {};
          const matched = bd.matched_concepts || [];
          const missing = bd.missing_concepts || [];
          return `
            <div class="card">
              <div class="card-header">
                <div>
                  <span class="badge badge-primary">Q${a.order_index} • ${escapeHtml(a.question_type)}</span>
                  ${a.faculty_override ? `<span class="badge badge-warning">Faculty Overridden</span>` : ""}
                  <h4 style="margin:8px 0 0;">${escapeHtml(a.prompt)}</h4>
                </div>
                <div style="text-align:right;min-width:110px;">
                  <div style="font-size:1.25rem;font-weight:750;">${a.final_marks} / ${a.max_marks}</div>
                  <div style="font-size:0.75rem;color:var(--text-muted);">AI Confidence: ${Math.round((a.ai_confidence || 0) * 100)}%</div>
                </div>
              </div>

              <div class="grid grid-2" style="margin-bottom:12px;">
                <div style="background:var(--bg);padding:12px;border-radius:9px;border:1px solid var(--border);">
                  <div style="font-size:0.75rem;font-weight:700;color:var(--text-muted);margin-bottom:4px;">YOUR SUBMITTED ANSWER</div>
                  <div style="font-size:0.88rem;">${escapeHtml(a.student_answer || "(No answer submitted)")}</div>
                </div>
                <div style="background:var(--bg);padding:12px;border-radius:9px;border:1px solid var(--border);">
                  <div style="font-size:0.75rem;font-weight:700;color:var(--text-muted);margin-bottom:4px;">REFERENCE / MODEL ANSWER</div>
                  <div style="font-size:0.88rem;">${escapeHtml(a.model_answer || "")}</div>
                </div>
              </div>

              <div style="font-size:0.86rem;margin-bottom:8px;">
                <strong>AI Evaluation Feedback:</strong> ${escapeHtml(a.ai_feedback)}
              </div>
              ${
                a.faculty_comment
                  ? `<div style="font-size:0.86rem;color:var(--warning);margin-bottom:8px;"><strong>Faculty Note:</strong> ${escapeHtml(a.faculty_comment)}</div>`
                  : ""
              }
              ${
                !["MCQ", "TRUE_FALSE", "PROGRAMMING"].includes(a.question_type)
                  ? `
                <div style="display:flex;gap:18px;flex-wrap:wrap;font-size:0.8rem;color:var(--text-muted);margin-bottom:8px;">
                  <span>TF-IDF Cosine: <strong>${Math.round((bd.tfidf_cosine || 0) * 100)}%</strong></span>
                  ${bd.bm25_similarity !== undefined ? `<span>BM25: <strong>${Math.round(bd.bm25_similarity * 100)}%</strong></span>` : ""}
                  <span>Concept Coverage: <strong>${Math.round((bd.concept_coverage || 0) * 100)}%</strong></span>
                </div>
                <div class="tag-list">
                  ${matched.map((c) => `<span class="tag tag-hit">+ ${escapeHtml(c)}</span>`).join("")}
                  ${missing.map((c) => `<span class="tag tag-miss">- ${escapeHtml(c)}</span>`).join("")}
                </div>
              `
                  : ""
              }
            </div>
          `;
        })
        .join("")}
    </div>

    <div class="card" style="margin-top:20px;">
      <h3 class="card-title" style="margin-bottom:10px;">Proctoring Activity Log (${proctor_logs.length} events)</h3>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Event</th><th>Severity</th><th>Details</th><th>Timestamp</th></tr></thead>
          <tbody>
            ${proctor_logs
              .slice(0, 15)
              .map(
                (l) => `
              <tr>
                <td><strong>${escapeHtml(l.event_type)}</strong></td>
                <td><span class="badge ${formatBadge(l.severity)}">${escapeHtml(l.severity)}</span></td>
                <td>${escapeHtml(l.details)}</td>
                <td style="color:var(--text-muted);font-size:0.8rem;">${escapeHtml(l.created_at)}</td>
              </tr>
            `
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;

  container.querySelector("#back-student-dash").onclick = () => renderStudentDashboard(container, user);
  container.querySelector("#print-report-btn").onclick = () => window.print();
}
