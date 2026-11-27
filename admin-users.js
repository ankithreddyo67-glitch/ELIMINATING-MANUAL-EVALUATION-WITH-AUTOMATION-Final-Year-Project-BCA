import { apiFetch, escapeHtml, showToast } from "./api.js";
import { removeRecord } from "./admin-delete.js";
import { editAccount } from "./admin-account.js";

export async function renderUserManagementTab(container, currentUser) {
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
