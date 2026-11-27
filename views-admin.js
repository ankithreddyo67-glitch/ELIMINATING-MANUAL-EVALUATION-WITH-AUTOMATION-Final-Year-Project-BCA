// Admin Portal: User Management, System Diagnostics, and Audit Trail

import { apiFetch, escapeHtml, formatBadge, showToast } from "/js/api.js";
import { renderAnalyticsTab, renderFacultyPortal } from "/js/views-faculty.js";

export async function renderAdminPortal(container, user, activeTab = "users") {
  if (["subjects", "assignments"].includes(activeTab)) {
    await renderRecords(container, activeTab);
    return;
  }
  if (activeTab === "exams") {
    await renderFacultyPortal(container, user, "exams");
    return;
  }
  if (activeTab === "analytics") {
    await renderAnalyticsTab(container);
    return;
  }
  if (activeTab === "audit") {
    await renderAuditLogsTab(container);
    return;
  }
  await renderUserManagementTab(container, user);
}

async function renderUserManagementTab(container, currentUser) {
  container.innerHTML = `<div class="card">Loading users &amp; system status...</div>`;
  const [usersRes, healthRes, analyticsRes] = await Promise.all([
    apiFetch("/api/users"),
    apiFetch("/api/health"),
    apiFetch("/api/analytics"),
  ]);

  const users = usersRes.users || [];

  container.innerHTML = `
    <div class="topbar">
      <div>
        <h1 class="page-title">System Administration &amp; Governance</h1>
        <p class="page-sub">Manage academic roles, monitor AI/CV engine capabilities, and verify system integrity.</p>
      </div>
    </div>

    <div class="grid grid-4" style="margin-bottom:20px;">
      <div class="card kpi-card">
        <span class="kpi-label">Total Accounts</span>
        <span class="kpi-value">${users.length}</span>
        <span class="kpi-foot">${analyticsRes.counts.total_students} students • ${analyticsRes.counts.total_faculty} faculty</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">NLP Grader</span>
        <span class="kpi-value" style="font-size:1.05rem;padding-top:6px;">Active</span>
        <span class="kpi-foot">${escapeHtml(healthRes.nlp_engine)}</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">CV Proctor Backend</span>
        <span class="kpi-value" style="font-size:1.05rem;padding-top:6px;">
          ${healthRes.opencv_enabled ? "OpenCV Haar + WebRTC" : "WebRTC YCbCr CV"}
        </span>
        <span class="kpi-foot">Client + Server telemetry active</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Total Submissions</span>
        <span class="kpi-value">${analyticsRes.counts.total_submissions}</span>
        <span class="kpi-foot">${analyticsRes.counts.total_exams} exams configured</span>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">User Directory</h3>
        <div class="assessment-actions">
          <label>Filter by role<select id="account-role-filter">
            <option value="">All roles</option><option>STUDENT</option><option>FACULTY</option><option>ADMIN</option>
          </select></label>
          <button type="button" class="btn btn-primary" id="add-account">Add account</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Department / ID</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${users
              .map(
                (u) => `
              <tr data-account-role="${u.role}">
                <td><strong>${escapeHtml(u.full_name)}</strong></td>
                <td>${escapeHtml(u.email)}</td>
                <td>${escapeHtml(u.department)} • ${escapeHtml(u.enrollment_no || "—")}</td>
                <td>
                  <select class="role-select" data-id="${u.id}" ${u.id === currentUser.id ? "disabled" : ""} style="width:130px;padding:5px 8px;">
                    <option value="STUDENT" ${u.role === "STUDENT" ? "selected" : ""}>STUDENT</option>
                    <option value="FACULTY" ${u.role === "FACULTY" ? "selected" : ""}>FACULTY</option>
                    <option value="ADMIN" ${u.role === "ADMIN" ? "selected" : ""}>ADMIN</option>
                  </select>
                </td>
                <td>
                  <span class="badge ${u.is_active ? "badge-success" : "badge-danger"}">
                    ${u.is_active ? "ACTIVE" : "DISABLED"}
                  </span>
                </td>
                <td>
                  ${
                    u.id === currentUser.id
                      ? `<span style="color:var(--text-muted);font-size:0.8rem;">Current Admin</span>`
                      : `<button class="btn btn-sm toggle-active-btn" data-id="${u.id}" data-active="${u.is_active ? 0 : 1}">
                           ${u.is_active ? "Disable" : "Enable"}
                         </button>`
                  }
                  <button class="btn btn-sm" data-edit-account="${u.id}">Edit</button>
                  ${u.id !== currentUser.id ? `<button class="btn btn-sm btn-danger" data-delete-account="${u.id}">Delete</button>` : ""}
                </td>
              </tr>
            `
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;

  const refresh = () => renderUserManagementTab(container, currentUser);
  const roleFilter = container.querySelector("#account-role-filter");
  roleFilter.onchange = () => {
    container.querySelectorAll("[data-account-role]").forEach((row) => {
      row.hidden = Boolean(roleFilter.value && row.dataset.accountRole !== roleFilter.value);
    });
  };
  container.querySelector("#add-account").onclick = () => editAccount({}, refresh);
  container.querySelectorAll("[data-edit-account]").forEach((button) => {
    button.onclick = () => editAccount(users.find((u) => u.id === Number(button.dataset.editAccount)), refresh);
  });
  container.querySelectorAll("[data-delete-account]").forEach((button) => {
    button.onclick = () => removeRecord(`/api/users/${button.dataset.deleteAccount}`, "Delete this account?", refresh);
  });

  container.querySelectorAll(".role-select").forEach((sel) => {
    sel.onchange = async () => {
      try {
        await apiFetch(`/api/users/${sel.dataset.id}`, {
          method: "PATCH",
          body: { role: sel.value },
        });
        showToast("User role updated.", "success");
        renderUserManagementTab(container, currentUser);
      } catch (err) {
        showToast(err.message, "error");
      }
    };
  });

  container.querySelectorAll(".toggle-active-btn").forEach((btn) => {
    btn.onclick = async () => {
      try {
        await apiFetch(`/api/users/${btn.dataset.id}`, {
          method: "PATCH",
          body: { is_active: btn.dataset.active === "1" },
        });
        showToast("Account status updated.", "success");
        renderUserManagementTab(container, currentUser);
      } catch (err) {
        showToast(err.message, "error");
      }
    };
  });
}

async function renderAuditLogsTab(container) {
  container.innerHTML = `<div class="card">Loading audit trail...</div>`;
  const res = await apiFetch("/api/audit-logs");
  const logs = res.logs || [];

  container.innerHTML = `
    <div class="topbar">
      <div>
        <h1 class="page-title">System Audit Trail</h1>
        <p class="page-sub">Immutable record of exam creation, grade overrides, result publishing, and RBAC changes.</p>
      </div>
    </div>

    <div class="card">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Target</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            ${logs
              .map(
                (l) => `
              <tr>
                <td style="font-size:0.8rem;color:var(--text-muted);">${escapeHtml(l.created_at)}</td>
                <td><strong>${escapeHtml(l.actor_name || "System")}</strong> <span class="badge ${formatBadge(l.actor_role)}">${escapeHtml(l.actor_role || "SYS")}</span></td>
                <td><strong>${escapeHtml(l.action)}</strong></td>
                <td>${escapeHtml(l.target_type)} #${escapeHtml(l.target_id ?? "")}</td>
                <td>${escapeHtml(l.details)}</td>
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

function openAdminForm(title, fields, save) {
  const dialog = document.createElement("dialog");
  dialog.className = "assessment-dialog";
  dialog.innerHTML = `<div class="card-header"><h2>${escapeHtml(title)}</h2>
    <button type="button" class="btn" data-close>Close</button></div>
    <form class="assessment-controls">${fields}<p role="alert" hidden></p>
    <button type="submit" class="btn btn-primary">Save</button></form>`;
  dialog.querySelector("[data-close]").onclick = () => dialog.close();
  dialog.addEventListener("close", () => dialog.remove(), { once: true });
  const form = dialog.querySelector("form");
  form.onsubmit = async (event) => {
    event.preventDefault();
    const saveButton = form.querySelector('[type="submit"]');
    const error = form.querySelector('[role="alert"]');
    error.hidden = true;
    saveButton.disabled = true;
    try {
      await save(new FormData(form));
      dialog.close();
    } catch (err) {
      error.textContent = err.message;
      error.hidden = false;
      saveButton.disabled = false;
    }
  };
  document.body.append(dialog);
  dialog.showModal();
}

async function removeRecord(path, message, refresh) {
  if (!window.confirm(message)) return;
  try {
    await apiFetch(path, { method: "DELETE" });
    await refresh();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function editAccount(user, refresh) {
  openAdminForm(user.id ? "Edit account" : "Add account", `
    <label>Full name<input name="full_name" required value="${escapeHtml(user.full_name)}"></label>
    <label>Email<input type="email" name="email" required value="${escapeHtml(user.email)}"></label>
    <label>Department<input name="department" value="${escapeHtml(user.department)}"></label>
    <label>Phone<input type="tel" name="phone" value="${escapeHtml(user.phone)}"></label>
    <label>Role<select name="role">${["STUDENT", "FACULTY", "ADMIN"].map((role) =>
      `<option ${user.role === role ? "selected" : ""}>${role}</option>`).join("")}</select></label>
    <label>${user.id ? "New password (optional)" : "Password"}<input type="password" minlength="6" name="password" ${user.id ? "" : "required"}></label>`, async (data) => {
    await apiFetch(user.id ? `/api/users/${user.id}` : "/api/users", {
      method: user.id ? "PATCH" : "POST", body: Object.fromEntries(data),
    });
    await refresh();
  });
}

