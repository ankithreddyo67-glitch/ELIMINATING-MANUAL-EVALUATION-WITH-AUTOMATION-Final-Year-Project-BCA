import { apiFetch, escapeHtml, formatBadge, showToast } from "./api.js";
import { renderSubmissionsTab } from "./faculty-submissions.js";

export async function renderFacultyAttemptInspector(container, user, attemptId) {
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
