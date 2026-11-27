import { apiFetch, showToast } from "./api.js";
import { renderExamRoom } from "./exam-room.js";

export function openProctorPreflightModal(container, user, examId) {
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
