// Authentication View (Login, Register, and One-Click Demo Access)

import { apiFetch, escapeHtml, saveSession, showToast } from "./api.js";

export function renderAuthView(container, onAuthenticated) {
  let mode = "login";

  function draw() {
    container.innerHTML = `
      <div class="auth-wrapper">
        <section class="auth-hero">
          <div style="display:flex;align-items:center;gap:12px;">
            <div class="brand-icon">AI</div>
            <div>
              <div class="brand-title" style="font-size:1.25rem;">AutoExam AI</div>
              <div class="brand-sub">Intelligent Automated Examination &amp; Evaluation Platform</div>
            </div>
          </div>

          <h1>Eliminating Manual Grading Bias &amp; Delays with Explainable AI</h1>
          <p style="color:var(--text-muted);max-width:600px;font-size:1rem;">
            An end-to-end academic assessment system combining Natural Language Processing for subjective answer evaluation,
            real-time Computer Vision proctoring, automated marks calculation, and transparent faculty audit workflows.
          </p>

          <div class="feature-grid">
            <div class="feature-item">
              <h4>NLP Subjective Grading</h4>
              <p>TF-IDF cosine similarity, BM25, bigram overlap, rubric concept coverage, and negation conflict checks.</p>
            </div>
            <div class="feature-item">
              <h4>Computer Vision Proctoring</h4>
              <p>Live webcam face-count, gaze offset, camera occlusion &amp; tab-switch monitoring with integrity scoring.</p>
            </div>
            <div class="feature-item">
              <h4>Explainable Faculty Review</h4>
              <p>Low-confidence flagging, matched vs. missing rubric concepts, and 1-click faculty mark override.</p>
            </div>
            <div class="feature-item">
              <h4>Automated Result Generation</h4>
              <p>Instant grade sheets, printable report cards, score distributions, and CSV exports.</p>
            </div>
          </div>
        </section>

        <section class="auth-panel">
          <div class="auth-card">
            <div class="tab-switch">
              <button type="button" id="tab-login" class="${mode === "login" ? "active" : ""}">Sign In</button>
              <button type="button" id="tab-register" class="${mode === "register" ? "active" : ""}">Create Account</button>
            </div>

            ${
              mode === "login"
                ? `
              <form id="login-form">
                <div class="form-group">
                  <label for="login-email">Academic Email</label>
                  <input id="login-email" type="email" required placeholder="student1@examai.edu" />
                </div>
                <div class="form-group">
                  <label for="login-password">Password</label>
                  <input id="login-password" type="password" required placeholder="Enter password" />
                </div>
                <button type="submit" class="btn btn-primary" style="width:100%;">Sign In to Portal</button>
              </form>
            `
                : `
              <form id="register-form">
                <div class="form-group">
                  <label for="reg-name">Full Name</label>
                  <input id="reg-name" type="text" required placeholder="e.g., Ananya Gupta" />
                </div>
                <div class="form-group">
                  <label for="reg-email">Email</label>
                  <input id="reg-email" type="email" required placeholder="ananya@examai.edu" />
                </div>
                <div class="grid grid-2">
                  <div class="form-group">
                    <label for="reg-role">Role</label>
                    <select id="reg-role">
                      <option value="STUDENT">Student</option>
                      <option value="FACULTY">Faculty</option>
                    </select>
                  </div>
                  <div class="form-group">
                    <label for="reg-enroll">Enrollment / ID</label>
                    <input id="reg-enroll" type="text" placeholder="CS2026-019" />
                  </div>
                </div>
                <div class="form-group">
                  <label for="reg-password">Password (min 6 chars)</label>
                  <input id="reg-password" type="password" minlength="6" required />
                </div>
                <button type="submit" class="btn btn-primary" style="width:100%;">Create Account</button>
              </form>
            `
            }

            <div class="demo-box">
              <div style="font-size:0.78rem;color:var(--text-muted);font-weight:600;">
                Quick Demo Login (Pre-seeded Academic Data)
              </div>
              <div class="demo-btns">
                <button type="button" class="btn btn-sm demo-login" data-email="student1@examai.edu" data-pass="Student@123">
                  Student
                </button>
                <button type="button" class="btn btn-sm demo-login" data-email="faculty@examai.edu" data-pass="Faculty@123">
                  Faculty
                </button>
                <button type="button" class="btn btn-sm demo-login" data-email="admin@examai.edu" data-pass="Admin@123">
                  Admin
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    `;

    container.querySelector("#tab-login").onclick = () => {
      mode = "login";
      draw();
    };
    container.querySelector("#tab-register").onclick = () => {
      mode = "register";
      draw();
    };

    const loginForm = container.querySelector("#login-form");
    if (loginForm) {
      loginForm.onsubmit = async (e) => {
        e.preventDefault();
        const email = container.querySelector("#login-email").value.trim();
        const password = container.querySelector("#login-password").value;
        await performLogin(email, password);
      };
    }

    const regForm = container.querySelector("#register-form");
    if (regForm) {
      regForm.onsubmit = async (e) => {
        e.preventDefault();
        try {
          const payload = {
            full_name: container.querySelector("#reg-name").value.trim(),
            email: container.querySelector("#reg-email").value.trim(),
            role: container.querySelector("#reg-role").value,
            enrollment_no: container.querySelector("#reg-enroll").value.trim(),
            password: container.querySelector("#reg-password").value,
          };
          const res = await apiFetch("/api/auth/register", { method: "POST", body: payload });
          saveSession(res.token, res.user);
          showToast(`Welcome, ${res.user.full_name}!`, "success");
          onAuthenticated(res.user);
        } catch (err) {
          showToast(err.message, "error");
        }
      };
    }

    container.querySelectorAll(".demo-login").forEach((btn) => {
      btn.onclick = () => performLogin(btn.dataset.email, btn.dataset.pass);
    });
  }

  async function performLogin(email, password) {
    try {
      const res = await apiFetch("/api/auth/login", {
        method: "POST",
        body: { email, password },
      });
      saveSession(res.token, res.user);
      showToast(`Signed in as ${res.user.full_name} (${res.user.role})`, "success");
      onAuthenticated(res.user);
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  draw();
}
