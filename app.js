// Main SPA Entry & Role-Based Navigation Shell

import {
  apiFetch,
  applyTheme,
  clearSession,
  escapeHtml,
  getSavedUser,
  getTheme,
  getToken,
  showToast,
} from "./api.js";
import { renderAdminPortal } from "./views-admin.js";
import { renderAuthView } from "./views-auth.js";
import { renderFacultyPortal } from "./views-faculty.js";
import { renderStudentPortal } from "./views-student.js";

const appEl = document.getElementById("app");
applyTheme(getTheme());

const NAV_BY_ROLE = {
  STUDENT: [
    { id: "dashboard", label: "Available Exams" },
    { id: "results", label: "My Results & AI Feedback" },
  ],
  FACULTY: [
    { id: "submissions", label: "Submissions & AI Review" },
    { id: "exams", label: "Exams & Question Bank" },
    { id: "nlp-sandbox", label: "AI NLP Grader Sandbox" },
    { id: "analytics", label: "Performance Analytics" },
  ],
  ADMIN: [
    { id: "users", label: "User & Role Management" },
    { id: "analytics", label: "System Analytics" },
    { id: "subjects", label: "Subjects" },
    { id: "assignments", label: "Exam Assignments" },
    { id: "exams", label: "Exams & Question Bank" },
    { id: "audit", label: "Audit Trail" },
  ],
};

let currentUser = null;
let currentTab = "";

async function bootstrap() {
  const token = getToken();
  const cached = getSavedUser();
  if (token && cached) {
    try {
      const me = await apiFetch("/api/auth/me");
      currentUser = me.user;
      currentTab = NAV_BY_ROLE[currentUser.role][0].id;
      renderShell();
      return;
    } catch {
      clearSession();
    }
  }
  renderLogin();
}

function renderLogin() {
  renderAuthView(appEl, (user) => {
    currentUser = user;
    currentTab = NAV_BY_ROLE[user.role][0].id;
    renderShell();
  });
}

function renderShell() {
  const navItems = NAV_BY_ROLE[currentUser.role] || [];
  const theme = getTheme();

  appEl.innerHTML = `
    <div class="app-shell">
      <aside class="sidebar">
        <div class="brand">
          <div class="brand-icon">AI</div>
          <div>
            <div class="brand-title">AutoExam AI</div>
            <div class="brand-sub">Automated Assessment</div>
          </div>
        </div>

        <nav class="nav-list">
          ${navItems
            .map(
              (item) => `
            <button class="nav-btn ${item.id === currentTab ? "active" : ""}" data-tab="${item.id}">
              <span>${escapeHtml(item.label)}</span>
            </button>
          `
            )
            .join("")}
        </nav>

        <div class="sidebar-footer">
          <div class="user-pill">
            <div class="name">${escapeHtml(currentUser.full_name)}</div>
            <div class="meta">${escapeHtml(currentUser.role)} • ${escapeHtml(currentUser.department || "")}</div>
          </div>
          <div style="display:flex;gap:8px;">
            <button id="theme-toggle-btn" class="btn btn-sm" style="flex:1;">
              ${theme === "dark" ? "Light Mode" : "Dark Mode"}
            </button>
            <button id="logout-btn" class="btn btn-sm btn-danger">Logout</button>
          </div>
        </div>
      </aside>

      <main class="main-area" id="main-content"></main>
    </div>
  `;

  appEl.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.onclick = () => {
      currentTab = btn.dataset.tab;
      renderShell();
    };
  });

  appEl.querySelector("#theme-toggle-btn").onclick = () => {
    const next = getTheme() === "dark" ? "light" : "dark";
    applyTheme(next);
    renderShell();
  };

  appEl.querySelector("#logout-btn").onclick = () => {
    clearSession();
    currentUser = null;
    showToast("Signed out.", "info");
    renderLogin();
  };

  const mainEl = appEl.querySelector("#main-content");
  routePortal(mainEl);
}

async function routePortal(mainEl) {
  try {
    if (currentUser.role === "STUDENT") {
      await renderStudentPortal(mainEl, currentUser, currentTab);
    } else if (currentUser.role === "FACULTY") {
      await renderFacultyPortal(mainEl, currentUser, currentTab);
    } else if (currentUser.role === "ADMIN") {
      await renderAdminPortal(mainEl, currentUser, currentTab);
    }
  } catch (err) {
    mainEl.innerHTML = `<div class="card"><h3>Error loading view</h3><p>${escapeHtml(err.message)}</p></div>`;
    showToast(err.message, "error");
  }
}

bootstrap();
