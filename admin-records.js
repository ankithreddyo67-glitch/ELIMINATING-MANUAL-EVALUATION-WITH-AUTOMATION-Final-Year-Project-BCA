import { apiFetch, escapeHtml, showToast } from "./api.js";
import { openAdminForm } from "./admin-form.js";
import { removeRecord } from "./admin-delete.js";

export async function renderRecords(container, tab) {
  const isSubject = tab === "subjects";
  const path = isSubject ? "/api/subjects" : "/api/exams";
  const [records, { users }] = await Promise.all([apiFetch(path), apiFetch("/api/users")]);
  const rows = isSubject ? records.subjects : records.exams;
  const refresh = () => renderRecords(container, tab);
  container.innerHTML = `<section class="card">
    <div class="card-header"><h1>${isSubject ? "Subjects" : "Exam Assignments"}</h1>
      ${isSubject ? '<button class="btn btn-primary" data-new>Add subject</button>' : ""}
    </div>
    <div class="table-wrap"><table><thead><tr><th>${isSubject ? "Subject" : "Exam"}</th>
      <th>${isSubject ? "Faculty" : "Access"}</th><th>Actions</th></tr></thead><tbody>
      ${rows.map((row) => `<tr><td>${escapeHtml(isSubject ? row.code + " · " + row.name : row.title)}</td>
        <td>${escapeHtml(isSubject ? row.faculty_name || "Unassigned" : row.restricted ? "Assigned students" : "All students")}</td>
        <td><button class="btn btn-sm" data-edit="${row.id}">${isSubject ? "Edit" : "Assign"}</button>
        ${isSubject ? `<button class="btn btn-sm btn-danger" data-delete="${row.id}">Delete</button>` : ""}</td></tr>`).join("")}
    </tbody></table></div>
  </section>`;
  function editSubject(subject = {}) {
    const faculty = users.filter((user) => user.role === "FACULTY" && user.is_active);
    openAdminForm(subject.id ? "Edit subject" : "Add subject", `
      <label>Code<input name="code" required value="${escapeHtml(subject.code)}"></label>
      <label>Name<input name="name" required value="${escapeHtml(subject.name)}"></label>
      <label>Description<textarea name="description">${escapeHtml(subject.description)}</textarea></label>
      <label>Faculty<select name="faculty_id"><option value="">Unassigned</option>
        ${faculty.map((u) => `<option value="${u.id}" ${u.id === subject.faculty_id ? "selected" : ""}>${escapeHtml(u.full_name)}</option>`).join("")}
      </select></label>`, async (data) => {
      await apiFetch(subject.id ? `${path}/${subject.id}` : path, {
        method: subject.id ? "PATCH" : "POST",
        body: { ...Object.fromEntries(data), faculty_id: Number(data.get("faculty_id")) || null },
      });
      await refresh();
    });
  }

  async function assign(exam) {
    const endpoint = `${path}/${exam.id}/assignments`;
    const { assignments } = await apiFetch(endpoint);
    const selected = new Set(assignments.map((a) => a.student_id));
    const due = assignments[0]?.due_at;
    const date = due ? new Date(due) : null;
    const local = date ? new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16) : "";
    openAdminForm(exam.title, `
      <label><input type="checkbox" name="restricted" ${exam.restricted ? "checked" : ""}> Limit access to assigned students</label>
      <label>Last time to start<input type="datetime-local" name="due_at" value="${local}"></label>
      <fieldset><legend>Active students</legend>
        ${users.filter((u) => u.role === "STUDENT" && u.is_active).map((u) => `
          <label><input type="checkbox" name="student_ids" value="${u.id}" ${selected.has(u.id) ? "checked" : ""}>
          ${escapeHtml(u.full_name)} (${escapeHtml(u.email)})</label>`).join("")}
      </fieldset>`, async (data) => {
      await apiFetch(endpoint, { method: "PATCH", body: {
        restricted: data.has("restricted"), student_ids: data.getAll("student_ids").map(Number),
        due_at: data.get("due_at") ? new Date(data.get("due_at")).toISOString() : null,
      } });
      await refresh();
    });
  }
  const newButton = container.querySelector("[data-new]");
  if (newButton) newButton.onclick = () => editSubject();
  container.querySelectorAll("[data-edit]").forEach((button) => {
    const row = rows.find((record) => record.id === Number(button.dataset.edit));
    button.onclick = () => isSubject ? editSubject(row) : assign(row).catch((err) => showToast(err.message, "error"));
  });
  container.querySelectorAll("[data-delete]").forEach((button) => {
    button.onclick = () => removeRecord(`${path}/${button.dataset.delete}`, "Delete this subject?", refresh);
  });
}
