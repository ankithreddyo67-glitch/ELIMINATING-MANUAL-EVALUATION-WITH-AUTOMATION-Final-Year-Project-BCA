import { apiFetch, showToast } from "./api.js";

export async function removeRecord(path, message, refresh) {
  if (!window.confirm(message)) return;
  try {
    await apiFetch(path, { method: "DELETE" });
    await refresh();
  } catch (err) {
    showToast(err.message, "error");
  }
}
