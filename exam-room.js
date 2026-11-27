import { apiFetch, escapeHtml, formatBadge, showToast } from "./api.js";
import { ExamProctorMonitor } from "./cv-proctor.js";
import { renderAttemptReportCard } from "./attempt-report.js";

export function renderExamRoom(container, user, sessionData) {
  const { attempt, exam, saved_answers } = sessionData;
  const questions = exam.questions || [];
  const answersMap = { ...saved_answers };
  let currentIdx = 0;
  const deadline = performance.now() + sessionData.remaining_seconds * 1000;
  let timerId = null;
  let submitted = false;
  const eventLogItems = [];

  container.innerHTML = `
    <div class="topbar">
      <div>
        <span class="badge badge-primary">${escapeHtml(exam.subject)}</span>
        <h1 class="page-title" style="margin-top:4px;">${escapeHtml(exam.title)}</h1>
      </div>
      <div style="display:flex;align-items:center;gap:12px;">
        <div id="exam-timer" class="timer-badge">30:00</div>
        <button id="submit-exam-btn" class="btn btn-success">Submit &amp; Auto-Grade</button>
      </div>
    </div>

    <div class="exam-room">
      <div>
        <div class="card" id="question-stage"></div>
        <div style="display:flex;justify-content:space-between;margin-top:14px;">
          <button id="prev-q-btn" class="btn">Previous</button>
          <button id="next-q-btn" class="btn btn-primary">Next Question</button>
        </div>
      </div>

      <aside class="card proctor-panel">
        <div class="card-header" style="margin-bottom:10px;">
          <h3 class="card-title">Live AI Proctoring</h3>
          <span id="integrity-badge" class="badge badge-success">100% CLEAR</span>
        </div>

        <div class="webcam-box">
          <video id="proctor-video" autoplay muted playsinline></video>
          <div class="webcam-overlay">
            <div class="hud-row">
              <span class="hud-chip" id="cv-face-chip">Faces: --</span>
              <span class="hud-chip" id="cv-light-chip">Light: --</span>
            </div>
            <div class="hud-row">
              <span class="hud-chip" id="cv-gaze-chip">Gaze Offset: --</span>
              <span class="hud-chip" id="cv-motion-chip">Motion: --</span>
            </div>
          </div>
        </div>

        <div style="margin-top:14px;">
          <div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);margin-bottom:8px;">Question Navigator</div>
          <div class="q-nav-grid" id="q-nav-grid"></div>
        </div>

        <div style="margin-top:14px;">
          <div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);">Proctoring Telemetry Feed</div>
          <p id="proctor-warning" class="event-item HIGH" role="status" hidden></p>
          <div class="event-feed" id="proctor-event-feed">
            <div class="event-item LOW">${sessionData.device_detection_enabled
              ? "Browser, camera and visible-device monitoring enabled."
              : "Browser and camera monitoring enabled. Device model unavailable."}</div>
          </div>
        </div>
      </aside>
    </div>
  `;

  const videoEl = container.querySelector("#proctor-video");
  const proctor = new ExamProctorMonitor({
    attemptId: attempt.id,
    videoEl,
    detectDevices: sessionData.device_detection_enabled,
    onWarning: (message) => {
      const warning = container.querySelector("#proctor-warning");
      if (warning) {
        warning.textContent = message;
        warning.hidden = false;
      }
    },
    onAutoSubmit: (result) => {
      if (submitted) return;
      submitted = true;
      clearInterval(timerId);
      proctor.stop();
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
      showToast("Exam submitted after reaching the configured warning limit.", "warning");
      renderAttemptReportCard(container, user, attempt.id, result);
    },
    onMetrics: (m) => {
      const fChip = container.querySelector("#cv-face-chip");
      const lChip = container.querySelector("#cv-light-chip");
      const gChip = container.querySelector("#cv-gaze-chip");
      const mChip = container.querySelector("#cv-motion-chip");
      if (fChip) fChip.textContent = `Faces: ${m.face_count}`;
      if (lChip) lChip.textContent = `Light: ${Math.round(m.mean_brightness)}`;
      if (gChip) gChip.textContent = `Offset: ${m.center_offset_x}`;
      if (mChip) mChip.textContent = `Motion: ${m.motion_score}`;
    },
    onIntegrityUpdate: (integ) => {
      const badge = container.querySelector("#integrity-badge");
      if (badge) {
        badge.className = `badge ${formatBadge(integ.risk_level)}`;
        badge.textContent = `${integ.integrity_score}% ${integ.risk_level}`;
      }
    },
    onEvent: (ev) => {
      eventLogItems.unshift(ev);
      const feed = container.querySelector("#proctor-event-feed");
      if (feed) {
        feed.innerHTML = eventLogItems
          .slice(0, 12)
          .map(
            (e) =>
              `<div class="event-item ${escapeHtml(e.severity)}"><strong>${escapeHtml(e.event_type)}</strong>: ${escapeHtml(e.details)}</div>`
          )
          .join("");
      }
      showToast(`Proctoring Alert: ${ev.event_type}`, "warning");
    },
  });

  proctor.startMonitoring();
  proctor.startCamera().then((res) => {
    if (!res.ok) {
      const fChip = container.querySelector("#cv-face-chip");
      if (fChip) fChip.textContent = "Cam Unavailable";
    }
  });

  function renderNav() {
    const navGrid = container.querySelector("#q-nav-grid");
    navGrid.innerHTML = questions
      .map((q, idx) => {
        const hasAns = Boolean((answersMap[q.id] || "").trim());
        const cls = idx === currentIdx ? "current" : hasAns ? "answered" : "";
        return `<button type="button" class="q-pill ${cls}" data-idx="${idx}">${idx + 1}</button>`;
      })
      .join("");
    navGrid.querySelectorAll(".q-pill").forEach((b) => {
      b.onclick = () => {
        currentIdx = Number(b.dataset.idx);
        renderQuestion();
      };
    });
  }

  const draftTimers = new Map();
  function scheduleDraftSave(qid, val) {
    clearTimeout(draftTimers.get(qid));
    draftTimers.set(qid, setTimeout(() => {
      draftTimers.delete(qid);
      apiFetch(`/api/attempts/${attempt.id}/draft`, {
        method: "POST",
        body: { question_id: qid, student_answer: val },
      }).catch(() => {});
    }, 450));
  }

  function renderQuestion() {
    const q = questions[currentIdx];
    const stage = container.querySelector("#question-stage");
    const currentAns = answersMap[q.id] || "";

    let inputHtml = "";
    if (["MCQ", "TRUE_FALSE"].includes(q.question_type)) {
      inputHtml = (q.options || [])
        .map((opt) => {
          const optKey = q.question_type === "TRUE_FALSE" ? String(opt).toUpperCase() : String(opt).charAt(0).toUpperCase();
          const selected = currentAns.toUpperCase() === optKey;
          return `
            <label class="mcq-option ${selected ? "selected" : ""}">
              <input type="radio" name="mcq_${q.id}" value="${escapeHtml(optKey)}" ${selected ? "checked" : ""} />
              <span>${escapeHtml(opt)}</span>
            </label>
          `;
        })
        .join("");
    } else {
      const rows = q.question_type === "SHORT" ? 3 : 7;
      const programming = q.question_type === "PROGRAMMING";
      inputHtml = `
        <div class="form-group" style="margin-top:12px;">
          <label for="ans-input-${q.id}">Your ${programming ? "Code" : "Answer"}</label>
          <textarea id="ans-input-${q.id}" rows="${rows}" ${programming ? 'spellcheck="false" class="code-answer"' : ""}>${escapeHtml(currentAns)}</textarea>
        </div>
      `;
    }

    stage.innerHTML = `
      <div class="card-header">
        <div>
          <span class="badge badge-primary">Question ${currentIdx + 1} of ${questions.length} • ${escapeHtml(q.question_type)}</span>
        </div>
        <span class="badge badge-muted">Max Marks: ${q.max_marks}</span>
      </div>
      <h3 style="margin:6px 0 14px;font-size:1.12rem;">${escapeHtml(q.prompt)}</h3>
      ${inputHtml}
    `;

    if (["MCQ", "TRUE_FALSE"].includes(q.question_type)) {
      stage.querySelectorAll(`input[name="mcq_${q.id}"]`).forEach((radio) => {
        radio.onchange = () => {
          answersMap[q.id] = radio.value;
          scheduleDraftSave(q.id, radio.value);
          renderQuestion();
        };
      });
    } else {
      const ta = stage.querySelector(`#ans-input-${q.id}`);
      ta.oninput = () => {
        answersMap[q.id] = ta.value;
        scheduleDraftSave(q.id, ta.value);
        renderNav();
      };
    }

    container.querySelector("#prev-q-btn").disabled = currentIdx === 0;
    container.querySelector("#next-q-btn").disabled = currentIdx === questions.length - 1;
    renderNav();
  }

  container.querySelector("#prev-q-btn").onclick = () => {
    if (currentIdx > 0) {
      currentIdx--;
      renderQuestion();
    }
  };
  container.querySelector("#next-q-btn").onclick = () => {
    if (currentIdx < questions.length - 1) {
      currentIdx++;
      renderQuestion();
    }
  };

  async function submitExam(autoTriggered = false) {
    if (submitted) return;
    submitted = true;
    if (timerId) clearInterval(timerId);
    proctor.stop();
    if (document.fullscreenElement && document.exitFullscreen) {
      document.exitFullscreen().catch(() => {});
    }

    const btn = container.querySelector("#submit-exam-btn");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Evaluating with AI...";
    }

    try {
      const payload = {};
      for (const q of questions) {
        payload[String(q.id)] = answersMap[q.id] || "";
      }
      const res = await apiFetch(`/api/attempts/${attempt.id}/submit`, {
        method: "POST",
        body: { answers: payload, auto_publish: true },
      });
      showToast(
        autoTriggered ? "Time expired — Exam auto-submitted & evaluated!" : "Exam submitted & AI-evaluated!",
        "success"
      );
      renderAttemptReportCard(container, user, res.attempt.id, res);
    } catch (err) {
      submitted = false;
      if (btn) {
        btn.disabled = false;
        btn.textContent = "Retry submission";
      }
      showToast(err.message, "error");
    }
  }

  container.querySelector("#submit-exam-btn").onclick = () => submitExam(false);

  timerId = setInterval(() => {
    const secondsLeft = Math.max(0, Math.ceil((deadline - performance.now()) / 1000));
    const timerEl = container.querySelector("#exam-timer");
    if (!timerEl) {
      clearInterval(timerId);
      proctor.stop();
      return;
    }
    const mins = Math.floor(Math.max(0, secondsLeft) / 60);
    const secs = Math.max(0, secondsLeft) % 60;
    timerEl.textContent = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
    if (secondsLeft <= 120) timerEl.classList.add("urgent");
    if (secondsLeft <= 0) {
      submitExam(true);
    }
  }, 1000);

  renderQuestion();
}
