import { renderSubmissionsTab } from "./faculty-submissions.js";
import { renderFacultyExamsTab } from "./faculty-exams.js";
import { renderNlpSandboxTab } from "./nlp-sandbox.js";
import { renderAnalyticsTab } from "./analytics-view.js";

// Faculty Portal: Evaluation Review & Override, Exam Builder, NLP Sandbox, Analytics

export async function renderFacultyPortal(container, user, activeTab = "submissions") {
  if (activeTab === "exams") {
    await renderFacultyExamsTab(container, user);
    return;
  }
  if (activeTab === "nlp-sandbox") {
    renderNlpSandboxTab(container);
    return;
  }
  if (activeTab === "analytics") {
    await renderAnalyticsTab(container);
    return;
  }
  await renderSubmissionsTab(container, user);
}

export { renderAnalyticsTab } from "./analytics-view.js";
