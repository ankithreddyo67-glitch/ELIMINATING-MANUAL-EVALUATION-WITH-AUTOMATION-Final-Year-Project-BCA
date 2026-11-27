import { apiFetch, escapeHtml, formatBadge } from "./api.js";

export async function renderAuditLogsTab(container) {
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
