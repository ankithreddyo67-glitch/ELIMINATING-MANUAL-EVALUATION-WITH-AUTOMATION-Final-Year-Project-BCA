import { apiFetch, escapeHtml } from "./api.js";
import { openAdminForm } from "./admin-form.js";

export function editAccount(user, refresh) {
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
