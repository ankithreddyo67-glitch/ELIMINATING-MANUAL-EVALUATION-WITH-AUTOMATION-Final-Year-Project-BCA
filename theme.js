const STORAGE_THEME_KEY = "autoexam_theme";

export function getTheme() {
  return localStorage.getItem(STORAGE_THEME_KEY) || "dark";
}

export function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem(STORAGE_THEME_KEY, theme);
}
