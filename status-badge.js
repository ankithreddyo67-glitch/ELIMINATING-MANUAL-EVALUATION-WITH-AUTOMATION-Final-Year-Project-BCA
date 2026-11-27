export function formatBadge(status) {
  const s = String(status || "").toUpperCase();
  if (["PUBLISHED", "CLEAR", "PASS", "PASSED", "ACTIVE"].includes(s)) return "badge-success";
  if (["EVALUATED", "WATCH", "MEDIUM"].includes(s)) return "badge-warning";
  if (["FLAGGED", "FAIL", "FAILED", "HIGH", "DISABLED"].includes(s)) return "badge-danger";
  if (["IN_PROGRESS", "SUBMITTED", "ADMIN", "FACULTY"].includes(s)) return "badge-primary";
  return "badge-muted";
}
