// Real-time Computer Vision Proctoring & Browser Telemetry Monitor

import { apiFetch } from "./api.js";

export class ExamProctorMonitor {
  constructor({ attemptId, videoEl, detectDevices, onMetrics, onIntegrityUpdate, onEvent, onWarning, onAutoSubmit }) {
    this.attemptId = attemptId;
    this.videoEl = videoEl;
    this.detectDevices = detectDevices;
    this.onWarning = onWarning;
    this.onAutoSubmit = onAutoSubmit;
    this.sampling = false;
    this.onMetrics = onMetrics || (() => {});
    this.onIntegrityUpdate = onIntegrityUpdate || (() => {});
    this.onEvent = onEvent || (() => {});

    this.stream = null;
    this.intervalId = null;
    this.canvas = document.createElement("canvas");
    this.canvas.width = 160;
    this.canvas.height = 120;
    this.ctx = this.canvas.getContext("2d", { willReadFrequently: true });
    this.prevGray = null;
    this.active = false;
    this.cameraAvailable = false;
    this._boundListeners = [];
    this._lastEventAt = {};
  }

  async startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this.cameraAvailable = false;
      return { ok: false, reason: "WebRTC camera API is unavailable in this browser context." };
    }
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false,
      });
      if (!this.active) {
        this.stream.getTracks().forEach((track) => track.stop());
        this.stream = null;
        return { ok: false, reason: "Exam monitoring ended." };
      }
      if (this.videoEl) {
        this.videoEl.srcObject = this.stream;
        await this.videoEl.play().catch(() => {});
      }
      this.cameraAvailable = true;
      return { ok: true };
    } catch (err) {
      this.cameraAvailable = false;
      return { ok: false, reason: err?.message || "Camera permission denied or no webcam found." };
    }
  }

  startMonitoring() {
    this.active = true;
    this._attachBrowserGuards();
    if (this.intervalId) clearInterval(this.intervalId);
    this.intervalId = setInterval(() => this._sampleFrameAndSend(), 2800);
  }

  stop() {
    this.active = false;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this._detachBrowserGuards();
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
  }

  analyzeCurrentFrame() {
    if (!this.cameraAvailable || !this.videoEl || this.videoEl.readyState < 2) {
      return null;
    }
    const W = this.canvas.width;
    const H = this.canvas.height;
    this.ctx.drawImage(this.videoEl, 0, 0, W, H);
    const imgData = this.ctx.getImageData(0, 0, W, H);
    const data = imgData.data;

    const gridW = 20;
    const gridH = 15;
    const cellW = W / gridW;
    const cellH = H / gridH;
    const skinGrid = new Uint16Array(gridW * gridH);
    const currGray = new Uint8Array(W * H);

    let lumaSum = 0;
    let motionDiffSum = 0;

    for (let y = 0; y < H; y++) {
      const gy = Math.min(gridH - 1, Math.floor(y / cellH));
      for (let x = 0; x < W; x++) {
        const idx = (y * W + x) * 4;
        const r = data[idx];
        const g = data[idx + 1];
        const b = data[idx + 2];

        const yVal = 0.299 * r + 0.587 * g + 0.114 * b;
        const cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b;
        const cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b;

        const pIdx = y * W + x;
        const grayByte = yVal | 0;
        currGray[pIdx] = grayByte;
        lumaSum += yVal;

        if (this.prevGray) {
          motionDiffSum += Math.abs(grayByte - this.prevGray[pIdx]);
        }

        // Skin chrominance heuristic in YCbCr space
        if (yVal > 45 && cb >= 77 && cb <= 128 && cr >= 133 && cr <= 175) {
          const gx = Math.min(gridW - 1, Math.floor(x / cellW));
          skinGrid[gy * gridW + gx] += 1;
        }
      }
    }

    const totalPixels = W * H;
    const meanBrightness = lumaSum / totalPixels;
    const motionScore = this.prevGray ? motionDiffSum / (totalPixels * 255) : 0;
    this.prevGray = currGray;

    // Connected-component clustering on skinGrid to estimate face regions
    const cellArea = cellW * cellH;
    const activeCells = new Uint8Array(gridW * gridH);
    for (let i = 0; i < skinGrid.length; i++) {
      if (skinGrid[i] >= cellArea * 0.35) activeCells[i] = 1;
    }

    const visited = new Uint8Array(gridW * gridH);
    const clusters = [];
    for (let gy = 0; gy < gridH; gy++) {
      for (let gx = 0; gx < gridW; gx++) {
        const start = gy * gridW + gx;
        if (!activeCells[start] || visited[start]) continue;
        const queue = [start];
        visited[start] = 1;
        let count = 0;
        let sumX = 0;
        let sumY = 0;
        while (queue.length > 0) {
          const cur = queue.pop();
          const cx = cur % gridW;
          const cy = Math.floor(cur / gridW);
          count++;
          sumX += cx + 0.5;
          sumY += cy + 0.5;
          for (let dy = -1; dy <= 1; dy++) {
            for (let dx = -1; dx <= 1; dx++) {
              const nx = cx + dx;
              const ny = cy + dy;
              if (nx >= 0 && nx < gridW && ny >= 0 && ny < gridH) {
                const nIdx = ny * gridW + nx;
                if (activeCells[nIdx] && !visited[nIdx]) {
                  visited[nIdx] = 1;
                  queue.push(nIdx);
                }
              }
            }
          }
        }
        // Filter tiny noise blobs; a real face occupies >= 4 macro cells
        if (count >= 4) {
          clusters.push({
            size: count,
            normX: (sumX / count) / gridW,
            normY: (sumY / count) / gridH,
          });
        }
      }
    }

    clusters.sort((a, b) => b.size - a.size);
    const faceCount = meanBrightness < 22 ? 0 : clusters.length;
    const primaryOffsetX = clusters.length > 0 ? Math.abs(clusters[0].normX - 0.5) : 0;

    return {
      engine: "WEBRTC_YCBCR_CV",
      face_count: faceCount,
      mean_brightness: Number(meanBrightness.toFixed(1)),
      center_offset_x: Number(primaryOffsetX.toFixed(3)),
      motion_score: Number(motionScore.toFixed(3)),
    };
  }

  captureSnapshotDataUrl() {
    if (!this.cameraAvailable || !this.videoEl || this.videoEl.readyState < 2) return null;
    try {
      const snapCanvas = document.createElement("canvas");
      snapCanvas.width = 320;
      snapCanvas.height = 240;
      const sctx = snapCanvas.getContext("2d");
      sctx.drawImage(this.videoEl, 0, 0, 320, 240);
      return snapCanvas.toDataURL("image/jpeg", 0.65);
    } catch {
      return null;
    }
  }

  async _sampleFrameAndSend() {
    if (!this.active || this.sampling) return;
    const metrics = this.analyzeCurrentFrame();
    if (!metrics) return;
    this.onMetrics(metrics);

    const potentialIssue =
      metrics.mean_brightness < 22 ||
      metrics.face_count === 0 ||
      metrics.face_count > 1 ||
      metrics.center_offset_x > 0.24 ||
      metrics.motion_score > 0.32;

    if (!potentialIssue && !this.detectDevices) return;

    const now = Date.now();
    if (this._lastEventAt["CV_FRAME"] && now - this._lastEventAt["CV_FRAME"] < 6000) {
      return;
    }
    this._lastEventAt["CV_FRAME"] = now;

    const snapshot_b64 = this.captureSnapshotDataUrl();
    this.sampling = true;
    try {
      const res = await apiFetch(`/api/attempts/${this.attemptId}/proctor`, {
        method: "POST",
        body: { event_type: "CV_FRAME", metrics, snapshot_b64 },
      });
      this._handleResponse(res);
    } catch {
      // A later sample can resume after a transient connection failure.
    } finally {
      this.sampling = false;
    }
  }

  async reportBrowserEvent(eventType, details) {
    if (!this.active) return;
    const now = Date.now();
    if (this._lastEventAt[eventType] && now - this._lastEventAt[eventType] < 3000) {
      return;
    }
    this._lastEventAt[eventType] = now;
    const snapshot_b64 = this.captureSnapshotDataUrl();
    try {
      const res = await apiFetch(`/api/attempts/${this.attemptId}/proctor`, {
        method: "POST",
        body: { event_type: eventType, details, snapshot_b64 },
      });
      this._handleResponse(res);
    } catch {
      // Browser alerts remain visible locally if the request fails.
    }
  }

  _handleResponse(res) {
    if (!this.active) return;
    if (res.integrity) this.onIntegrityUpdate(res.integrity);
    res.logged_events?.forEach((event) => this.onEvent(event));
    if (res.auto_submitted && res.attempt_detail) this.onAutoSubmit?.(res.attempt_detail);
  }

  _addListener(target, type, fn) {
    target.addEventListener(type, fn);
    this._boundListeners.push({ target, type, fn });
  }

  _attachBrowserGuards() {
    this._addListener(document, "visibilitychange", () => {
      if (document.hidden) {
        this.onWarning?.("The exam tab was hidden. Stay on the exam page.");
        this.reportBrowserEvent("TAB_SWITCH", "Exam tab became hidden.");
      }
    });
    const guardExternalLink = (event) => {
      const link = event.target.closest?.("a[href]");
      if (!link) return;
      const destination = new URL(link.href, location.href);
      if (["http:", "https:"].includes(destination.protocol) && destination.origin !== location.origin) {
        event.preventDefault();
        this.onWarning?.("External links are blocked during the exam.");
        this.reportBrowserEvent("EXTERNAL_NAVIGATION_ATTEMPT", "Blocked an external link from the exam page.");
      }
    };
    this._addListener(document, "click", guardExternalLink);
    this._addListener(document, "auxclick", guardExternalLink);
    this._addListener(window, "blur", () => {
      if (this.active && !document.hidden) {
        this.reportBrowserEvent("WINDOW_BLUR", "Examination window lost focus.");
      }
    });
    this._addListener(document, "fullscreenchange", () => {
      if (this.active && !document.fullscreenElement) {
        this.reportBrowserEvent("FULLSCREEN_EXIT", "Candidate exited fullscreen examination mode.");
      }
    });
    this._addListener(document, "copy", (e) => {
      e.preventDefault();
      this.reportBrowserEvent("COPY_PASTE_ATTEMPT", "Blocked copy attempt during exam.");
    });
    this._addListener(document, "paste", (e) => {
      const target = e.target;
      // Allow pasting only inside textarea? No, block paste during proctored exam to discourage external answer pasting
      e.preventDefault();
      if (target) {
        this.reportBrowserEvent("COPY_PASTE_ATTEMPT", "Blocked paste attempt during exam.");
      }
    });
    this._addListener(document, "contextmenu", (e) => {
      e.preventDefault();
      this.reportBrowserEvent("RIGHT_CLICK_ATTEMPT", "Context menu disabled during proctored exam.");
    });
    this._addListener(document, "keydown", (e) => {
      if (
        e.key === "F12" ||
        (e.ctrlKey && e.shiftKey && ["I", "J", "C"].includes(e.key.toUpperCase()))
      ) {
        e.preventDefault();
        this.reportBrowserEvent("DEVTOOLS_SHORTCUT", `Blocked developer shortcut (${e.key}).`);
      }
    });
  }

  _detachBrowserGuards() {
    for (const { target, type, fn } of this._boundListeners) {
      target.removeEventListener(type, fn);
    }
    this._boundListeners = [];
  }
}
