const STORAGE_TOKEN_KEY = "autoexam_token";

const STORAGE_USER_KEY = "autoexam_user";

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
