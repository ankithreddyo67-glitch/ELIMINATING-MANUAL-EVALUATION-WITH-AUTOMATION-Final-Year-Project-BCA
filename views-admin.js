import { renderAnalyticsTab, renderFacultyPortal } from "./views-faculty.js";
import { renderUserManagementTab } from "./admin-users.js";
import { renderAuditLogsTab } from "./admin-audit.js";
import { renderRecords } from "./admin-records.js";

// Admin Portal: User Management, System Diagnostics, and Audit Trail

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

export { renderRecords } from "./admin-records.js";
