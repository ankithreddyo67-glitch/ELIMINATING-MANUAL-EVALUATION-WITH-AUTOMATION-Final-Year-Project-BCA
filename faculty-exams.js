import { apiFetch, escapeHtml, formatBadge, getToken, showToast } from "./api.js";
import { createExamDialog, editDraftPaper, editExamSchedule, renderQuestionBank, showExamPaper } from "./question-bank.js";

export async function renderFacultyExamsTab(container, user) {
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
