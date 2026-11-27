import { renderStudentDashboard } from "./student-dashboard.js";
import { renderStudentResultsList } from "./student-results.js";

// Student Portal: Dashboard, Proctored Exam Room, and AI Result Report Card

export async function renderStudentPortal(container, user, activeTab = "dashboard") {
  if (activeTab === "results") {
    await renderStudentResultsList(container, user);
    return;
  }
  await renderStudentDashboard(container, user);
}

export { renderAttemptReportCard } from "./attempt-report.js";
