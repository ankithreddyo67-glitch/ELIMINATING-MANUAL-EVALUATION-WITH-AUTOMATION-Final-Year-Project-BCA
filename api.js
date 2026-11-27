// REST API client and shared UI helpers

const STORAGE_TOKEN_KEY = "autoexam_token";
const STORAGE_USER_KEY = "autoexam_user";
const STORAGE_THEME_KEY = "autoexam_theme";

export function getToken() {
  return localStorage.getItem(STORAGE_TOKEN_KEY) || "";
}

export function getSavedUser() {
  try {
    const raw = localStorage.getItem(STORAGE_USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveSession(token, user) {
  localStorage.setItem(STORAGE_TOKEN_KEY, token);
  localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(STORAGE_TOKEN_KEY);
  localStorage.removeItem(STORAGE_USER_KEY);
}

export function getTheme() {
  return localStorage.getItem(STORAGE_THEME_KEY) || "dark";
}

export function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem(STORAGE_THEME_KEY, theme);
}

export function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => {
    el.remove();
  }, 4200);
}

export async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    ...(options.headers || {}),
  };
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(path, {
    ...options,
    headers,
    body: options.body && typeof options.body !== "string" ? JSON.stringify(options.body) : options.body,
  });

  if (options.rawResponse) {
    if (!res.ok) {
      throw new Error(`Request failed (${res.status})`);
    }
    return res;
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `Request failed (${res.status})`);
  }
  return data;
}

export function formatBadge(status) {
  const s = String(status || "").toUpperCase();
  if (["PUBLISHED", "CLEAR", "PASS", "PASSED", "ACTIVE"].includes(s)) return "badge-success";
  if (["EVALUATED", "WATCH", "MEDIUM"].includes(s)) return "badge-warning";
  if (["FLAGGED", "FAIL", "FAILED", "HIGH", "DISABLED"].includes(s)) return "badge-danger";
  if (["IN_PROGRESS", "SUBMITTED", "ADMIN", "FACULTY"].includes(s)) return "badge-primary";
  return "badge-muted";
}
