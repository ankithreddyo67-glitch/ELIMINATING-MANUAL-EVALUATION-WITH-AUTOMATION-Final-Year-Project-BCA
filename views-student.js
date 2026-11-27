// Student Portal: Dashboard, Proctored Exam Room, and AI Result Report Card

import { apiFetch, escapeHtml, formatBadge, showToast } from "/js/api.js";
import { ExamProctorMonitor } from "/js/cv-proctor.js";

export async function renderStudentPortal(container, user, activeTab = "dashboard") {
  if (activeTab === "results") {
    await renderStudentResultsList(container, user);
    return;
  }
  await renderStudentDashboard(container, user);
}

async function renderStudentDashboard(container, user) {
  container.innerHTML = `<div class="card">Loading examinations...</div>`;
  const [examData, attemptData] = await Promise.all([
    apiFetch("/api/exams"),
    apiFetch("/api/attempts"),
  ]);

  const exams = examData.exams || [];
  const attempts = attemptData.attempts || [];
  const completed = attempts.filter((a) => a.status !== "IN_PROGRESS");
  const avgPct = completed.length
    ? (completed.reduce((s, a) => s + Number(a.percentage || 0), 0) / completed.length).toFixed(1)
    : "—";
  const avgIntegrity = completed.length
    ? (completed.reduce((s, a) => s + Number(a.integrity_score || 100), 0) / completed.length).toFixed(1)
    : "100.0";

  container.innerHTML = `
    <div class="topbar">
      <div>
        <h1 class="page-title">Student Examination Portal</h1>
        <p class="page-sub">Welcome back, ${escapeHtml(user.full_name)} (${escapeHtml(user.enrollment_no || user.department)})</p>
      </div>
    </div>

    <div class="grid grid-4" style="margin-bottom:22px;">
      <div class="card kpi-card">
        <span class="kpi-label">Available Exams</span>
        <span class="kpi-value">${exams.length}</span>
        <span class="kpi-foot">Active published assessments</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Completed</span>
        <span class="kpi-value">${completed.length}</span>
        <span class="kpi-foot">Auto-evaluated submissions</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Average Score</span>
        <span class="kpi-value">${avgPct}${avgPct === "—" ? "" : "%"}</span>
        <span class="kpi-foot">Combined objective &amp; NLP subjective</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Integrity Index</span>
        <span class="kpi-value">${avgIntegrity}%</span>
        <span class="kpi-foot">CV &amp; browser proctoring score</span>
      </div>
    </div>

    <div class="card" style="margin-bottom:22px;">
      <div class="card-header">
        <div>
          <h3 class="card-title">Published Examinations</h3>
          <p class="page-sub">Launch a proctored exam or review your instant AI-graded report card.</p>
        </div>
      </div>
      <div class="grid grid-2">
        ${exams
          .map((ex) => {
            const att = ex.my_attempt;
            const statusText = att ? att.status : "NOT_STARTED";
            let actionBtn = `<button class="btn btn-primary start-exam-btn" data-exam-id="${ex.id}">Start Proctored Exam</button>`;
            if (att && att.status === "IN_PROGRESS") {
              actionBtn = `<button class="btn btn-primary start-exam-btn" data-exam-id="${ex.id}">Resume Exam</button>`;
            } else if (att) {
              actionBtn = `<button class="btn view-report-btn" data-attempt-id="${att.id}">View AI Report Card</button>`;
            }
            if (!att && ex.opens_at && Date.now() < Date.parse(ex.opens_at)) {
              actionBtn = '<span class="badge badge-muted">Scheduled · refresh after opening</span>';
            } else if (!att && [ex.closes_at, ex.assignment_due_at].some((date) => date && Date.now() >= Date.parse(date))) {
              actionBtn = '<span class="badge badge-muted">Start window closed</span>';
            }
            return `
              <div class="card" style="background:var(--bg-soft);box-shadow:none;">
                <div class="card-header">
                  <div>
                    <span class="badge badge-primary">${escapeHtml(ex.subject)}</span>
                    <h4 style="margin:8px 0 4px;">${escapeHtml(ex.title)}</h4>
                  </div>
                  <span class="badge ${formatBadge(statusText)}">${escapeHtml(statusText.replace("_", " "))}</span>
                </div>
                <p style="font-size:0.86rem;color:var(--text-muted);margin:0 0 12px;">${escapeHtml(ex.description)}</p>
                <div style="display:flex;gap:14px;flex-wrap:wrap;font-size:0.82rem;color:var(--text-muted);margin-bottom:14px;">
                  <span>Questions: <strong>${ex.question_count}</strong></span>
                  <span>Total Marks: <strong>${ex.total_marks}</strong></span>
                  ${ex.assignment_due_at ? `<span>Assignment deadline: <strong>${escapeHtml(new Date(ex.assignment_due_at).toLocaleString())}</strong></span>` : ""}
                  <span>Duration: <strong>${ex.duration_minutes} min</strong></span>
                  ${ex.opens_at ? `<span>Opens: <strong>${escapeHtml(new Date(ex.opens_at).toLocaleString())}</strong></span>` : ""}
                  ${ex.closes_at ? `<span>Last start: <strong>${escapeHtml(new Date(ex.closes_at).toLocaleString())}</strong></span>` : ""}
                  <span>Proctoring: <strong>${ex.proctoring_enabled ? ex.proctoring_strictness : "OFF"}</strong></span>
                </div>
                ${
                  att && att.status !== "IN_PROGRESS"
                    ? `<div style="margin-bottom:12px;font-size:0.86rem;">
                         Score: <strong>${att.total_score}/${att.max_score} (${att.percentage}%)</strong> • Grade: <strong>${escapeHtml(att.grade)}</strong> • Integrity: <strong>${att.integrity_score}%</strong>
                       </div>`
                    : ""
                }
                ${actionBtn}
              </div>
            `;
          })
          .join("")}
      </div>
    </div>
  `;

  container.querySelectorAll(".start-exam-btn").forEach((btn) => {
    btn.onclick = () => openProctorPreflightModal(container, user, Number(btn.dataset.examId));
  });
  container.querySelectorAll(".view-report-btn").forEach((btn) => {
    btn.onclick = () => renderAttemptReportCard(container, user, Number(btn.dataset.attemptId));
  });
}

async function renderStudentResultsList(container, user) {
  container.innerHTML = `<div class="card">Loading your results...</div>`;
  const data = await apiFetch("/api/attempts");
  const attempts = data.attempts || [];

  container.innerHTML = `
    <div class="topbar">
      <div>
        <h1 class="page-title">My Results &amp; AI Evaluations</h1>
        <p class="page-sub">Inspect per-question NLP feedback, matched rubric concepts, and integrity scores.</p>
      </div>
    </div>
    <div class="card">
      ${
        attempts.length === 0
          ? `<p style="color:var(--text-muted);">No examination attempts recorded yet.</p>`
          : `
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Exam</th>
                <th>Status</th>
                <th>Objective</th>
                <th>Subjective (NLP)</th>
                <th>Total</th>
                <th>Grade</th>
                <th>Integrity</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${attempts
                .map(
                  (a) => `
                <tr>
                  <td>
                    <strong>${escapeHtml(a.exam_title)}</strong>
                    <div style="font-size:0.78rem;color:var(--text-muted);">${escapeHtml(a.exam_subject)}</div>
                  </td>
                  <td><span class="badge ${formatBadge(a.status)}">${escapeHtml(a.status)}</span></td>
                  <td>${a.objective_score}</td>
                  <td>${a.subjective_score}</td>
                  <td><strong>${a.total_score}/${a.max_score}</strong> (${a.percentage}%)</td>
                  <td><span class="badge ${a.passed ? "badge-success" : "badge-danger"}">${escapeHtml(a.grade)}</span></td>
                  <td><span class="badge ${formatBadge(a.risk_level)}">${a.integrity_score}% (${escapeHtml(a.risk_level)})</span></td>
                  <td>
                    <button class="btn btn-sm btn-primary open-report" data-id="${a.id}">Report Card</button>
                  </td>
                </tr>
              `
                )
                .join("")}
            </tbody>
          </table>
        </div>
      `
      }
    </div>
  `;

  container.querySelectorAll(".open-report").forEach((btn) => {
    btn.onclick = () => renderAttemptReportCard(container, user, Number(btn.dataset.id));
  });
}

function openProctorPreflightModal(container, user, examId) {
  const modal = document.createElement("div");
  modal.className = "modal-backdrop";
  modal.innerHTML = `
    <div class="modal-card">
      <div class="card-header">
        <div>
          <h3 class="card-title">Pre-Exam AI Proctoring &amp; Environment Check</h3>
          <p class="page-sub">Webcam computer vision &amp; browser integrity monitoring will run during your attempt.</p>
        </div>
      </div>

      <div class="webcam-box" style="margin-bottom:14px;">
        <video id="preflight-video" autoplay muted playsinline></video>
        <div class="webcam-overlay">
          <div class="hud-row">
            <span class="hud-chip" id="preflight-cam-status">Initializing camera...</span>
          </div>
        </div>
      </div>

      <ul style="font-size:0.86rem;color:var(--text-muted);padding-left:18px;margin:0 0 16px;">
        <li>Keep a single face clearly visible and well-lit inside the frame.</li>
        <li>Avoid switching tabs, exiting fullscreen, or copy-pasting external text.</li>
        <li>Subjective answers are graded automatically via NLP concept &amp; semantic alignment.</li>
      </ul>

      <div style="display:flex;justify-content:flex-end;gap:10px;">
        <button type="button" class="btn" id="cancel-preflight">Cancel</button>
        <button type="button" class="btn btn-primary" id="begin-exam-btn">Enter Exam Room</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  const videoEl = modal.querySelector("#preflight-video");
  const statusEl = modal.querySelector("#preflight-cam-status");
  let previewStream = null;

  (async () => {
    if (navigator.mediaDevices?.getUserMedia) {
      try {
        previewStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        videoEl.srcObject = previewStream;
        statusEl.textContent = "Webcam Ready (CV Active)";
      } catch {
        statusEl.textContent = "No Webcam / Permission Denied — Telemetry Mode";
      }
    } else {
      statusEl.textContent = "WebRTC Unavailable — Browser Telemetry Mode";
    }
  })();

  const cleanupPreview = () => {
    if (previewStream) {
      previewStream.getTracks().forEach((t) => t.stop());
      previewStream = null;
    }
    modal.remove();
  };

  modal.querySelector("#cancel-preflight").onclick = cleanupPreview;
  modal.querySelector("#begin-exam-btn").onclick = async () => {
    cleanupPreview();
    try {
      const started = await apiFetch(`/api/exams/${examId}/start`, { method: "POST", body: {} });
      if (document.documentElement.requestFullscreen) {
        document.documentElement.requestFullscreen().catch(() => {});
      }
      renderExamRoom(container, user, started);
    } catch (err) {
      showToast(err.message, "error");
    }
  };
}

function renderExamRoom(container, user, sessionData) {
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

export async function renderAttemptReportCard(container, user, attemptId, preloaded = null) {
  const data = preloaded || (await apiFetch(`/api/attempts/${attemptId}`));
  const { attempt, answers, proctor_logs } = data;

  container.innerHTML = `
    <div class="topbar no-print">
      <div>
        <h1 class="page-title">Automated Assessment Report Card</h1>
        <p class="page-sub">${escapeHtml(attempt.exam_title)} • ${escapeHtml(attempt.student_name)}</p>
      </div>
      <div style="display:flex;gap:10px;">
        <button class="btn" id="back-student-dash">Back to Dashboard</button>
        <button class="btn btn-primary" id="print-report-btn">Print / Save PDF</button>
      </div>
    </div>

    <div class="card" style="margin-bottom:20px;">
      <div class="grid grid-4">
        <div class="kpi-card">
          <span class="kpi-label">Final Score</span>
          <span class="kpi-value">${attempt.total_score} / ${attempt.max_score}</span>
          <span class="kpi-foot">${attempt.percentage}% (${attempt.passed ? "PASSED" : "FAILED"})</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Grade</span>
          <span class="kpi-value">${escapeHtml(attempt.grade)}</span>
          <span class="kpi-foot">Objective: ${attempt.objective_score} • Subjective: ${attempt.subjective_score}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Proctoring Integrity</span>
          <span class="kpi-value">${attempt.integrity_score}%</span>
          <span class="kpi-foot"><span class="badge ${formatBadge(attempt.risk_level)}">${escapeHtml(attempt.risk_level)}</span></span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Evaluation Status</span>
          <span class="kpi-value" style="font-size:1.25rem;padding-top:6px;">
            <span class="badge ${formatBadge(attempt.status)}">${escapeHtml(attempt.status)}</span>
          </span>
          <span class="kpi-foot">${escapeHtml(attempt.faculty_remarks || "Auto-graded via ML/NLP pipeline")}</span>
        </div>
      </div>
    </div>

    <div class="grid" style="gap:16px;">
      ${answers
        .map((a) => {
          const bd = a.ai_breakdown || {};
          const matched = bd.matched_concepts || [];
          const missing = bd.missing_concepts || [];
          return `
            <div class="card">
              <div class="card-header">
                <div>
                  <span class="badge badge-primary">Q${a.order_index} • ${escapeHtml(a.question_type)}</span>
                  ${a.faculty_override ? `<span class="badge badge-warning">Faculty Overridden</span>` : ""}
                  <h4 style="margin:8px 0 0;">${escapeHtml(a.prompt)}</h4>
                </div>
                <div style="text-align:right;min-width:110px;">
                  <div style="font-size:1.25rem;font-weight:750;">${a.final_marks} / ${a.max_marks}</div>
                  <div style="font-size:0.75rem;color:var(--text-muted);">AI Confidence: ${Math.round((a.ai_confidence || 0) * 100)}%</div>
                </div>
              </div>

              <div class="grid grid-2" style="margin-bottom:12px;">
                <div style="background:var(--bg);padding:12px;border-radius:9px;border:1px solid var(--border);">
                  <div style="font-size:0.75rem;font-weight:700;color:var(--text-muted);margin-bottom:4px;">YOUR SUBMITTED ANSWER</div>
                  <div style="font-size:0.88rem;">${escapeHtml(a.student_answer || "(No answer submitted)")}</div>
                </div>
                <div style="background:var(--bg);padding:12px;border-radius:9px;border:1px solid var(--border);">
                  <div style="font-size:0.75rem;font-weight:700;color:var(--text-muted);margin-bottom:4px;">REFERENCE / MODEL ANSWER</div>
                  <div style="font-size:0.88rem;">${escapeHtml(a.model_answer || "")}</div>
                </div>
              </div>

              <div style="font-size:0.86rem;margin-bottom:8px;">
                <strong>AI Evaluation Feedback:</strong> ${escapeHtml(a.ai_feedback)}
              </div>
              ${
                a.faculty_comment
                  ? `<div style="font-size:0.86rem;color:var(--warning);margin-bottom:8px;"><strong>Faculty Note:</strong> ${escapeHtml(a.faculty_comment)}</div>`
                  : ""
              }
              ${
                !["MCQ", "TRUE_FALSE", "PROGRAMMING"].includes(a.question_type)
                  ? `
                <div style="display:flex;gap:18px;flex-wrap:wrap;font-size:0.8rem;color:var(--text-muted);margin-bottom:8px;">
                  <span>TF-IDF Cosine: <strong>${Math.round((bd.tfidf_cosine || 0) * 100)}%</strong></span>
                  ${bd.bm25_similarity !== undefined ? `<span>BM25: <strong>${Math.round(bd.bm25_similarity * 100)}%</strong></span>` : ""}
                  <span>Concept Coverage: <strong>${Math.round((bd.concept_coverage || 0) * 100)}%</strong></span>
                </div>
                <div class="tag-list">
                  ${matched.map((c) => `<span class="tag tag-hit">+ ${escapeHtml(c)}</span>`).join("")}
                  ${missing.map((c) => `<span class="tag tag-miss">- ${escapeHtml(c)}</span>`).join("")}
                </div>
              `
                  : ""
              }
            </div>
          `;
        })
        .join("")}
    </div>

    <div class="card" style="margin-top:20px;">
      <h3 class="card-title" style="margin-bottom:10px;">Proctoring Activity Log (${proctor_logs.length} events)</h3>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Event</th><th>Severity</th><th>Details</th><th>Timestamp</th></tr></thead>
          <tbody>
            ${proctor_logs
              .slice(0, 15)
              .map(
                (l) => `
              <tr>
                <td><strong>${escapeHtml(l.event_type)}</strong></td>
                <td><span class="badge ${formatBadge(l.severity)}">${escapeHtml(l.severity)}</span></td>
                <td>${escapeHtml(l.details)}</td>
                <td style="color:var(--text-muted);font-size:0.8rem;">${escapeHtml(l.created_at)}</td>
              </tr>
            `
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;

  container.querySelector("#back-student-dash").onclick = () => renderStudentDashboard(container, user);
  container.querySelector("#print-report-btn").onclick = () => window.print();
}
