import { apiFetch, escapeHtml, showToast } from "./api.js";

export function renderNlpSandboxTab(container) {
  container.innerHTML = `
    <div class="topbar">
      <div>
        <h1 class="page-title">Live AI Subjective Grading Sandbox</h1>
        <p class="page-sub">Test the ML/NLP evaluation ensemble (TF-IDF Cosine, BM25, Bigram F1, Rubric Coverage, Negation Guard).</p>
      </div>
    </div>

    <div class="grid grid-2">
      <div class="card">
        <form id="nlp-sandbox-form">
          <div class="grid grid-2">
            <div class="form-group">
              <label>Question Type</label>
              <select id="sb-type">
                <option value="SUBJECTIVE" selected>SUBJECTIVE</option>
                <option value="SHORT">SHORT</option>
              </select>
            </div>
            <div class="form-group">
              <label>Max Marks</label>
              <input id="sb-marks" type="number" value="10" min="1" step="0.5" />
            </div>
          </div>
          <div class="form-group">
            <label>Reference / Model Answer</label>
            <textarea id="sb-model" rows="4">Gradient descent is an iterative optimization algorithm used to minimize a loss function by updating model parameters in the opposite direction of the gradient scaled by the learning rate.</textarea>
          </div>
          <div class="form-group">
            <label>Rubric Key Concepts (comma-separated)</label>
            <input id="sb-keywords" value="iterative optimization, loss function, parameters, gradient, learning rate" />
          </div>
          <div class="form-group">
            <label>Sample Student Answer</label>
            <textarea id="sb-student" rows="4">Gradient descent minimizes the loss function iteratively by adjusting weights using the learning rate along the negative gradient.</textarea>
          </div>
          <button type="submit" class="btn btn-primary">Evaluate with ML/NLP Engine</button>
        </form>
      </div>

      <div class="card" id="sb-output">
        <h3 class="card-title">Evaluation Breakdown</h3>
        <p style="color:var(--text-muted);font-size:0.88rem;">Click "Evaluate with ML/NLP Engine" to inspect similarity signals, concept coverage, confidence, and feedback.</p>
      </div>
    </div>
  `;

  async function runPreview() {
    const out = container.querySelector("#sb-output");
    try {
      const res = await apiFetch("/api/nlp/preview", {
        method: "POST",
        body: {
          question_type: container.querySelector("#sb-type").value,
          max_marks: Number(container.querySelector("#sb-marks").value),
          model_answer: container.querySelector("#sb-model").value,
          keywords: container.querySelector("#sb-keywords").value,
          student_answer: container.querySelector("#sb-student").value,
        },
      });
      const ev = res.evaluation;
      const bd = ev.breakdown || {};
      out.innerHTML = `
        <div class="card-header">
          <h3 class="card-title">Evaluation Breakdown</h3>
          <span class="badge ${ev.needs_review ? "badge-warning" : "badge-success"}">
            Confidence: ${Math.round(ev.confidence * 100)}%
          </span>
        </div>
        <div style="font-size:2rem;font-weight:800;margin-bottom:10px;">
          ${ev.awarded_marks} <span style="font-size:1rem;color:var(--text-muted);">/ ${ev.max_marks} marks</span>
        </div>
        <p style="font-size:0.9rem;margin-bottom:16px;">${escapeHtml(ev.feedback)}</p>

        ${[
          ["Concept Coverage", bd.concept_coverage],
          ["TF-IDF Cosine Similarity", bd.tfidf_cosine],
          ["BM25 Term Relevance", bd.bm25_similarity],
          ["Bigram Phrase F1", bd.bigram_f1],
          ["Length Adequacy", bd.length_adequacy],
        ]
          .filter(([, val]) => val !== undefined)
          .map(
            ([label, val]) => `
          <div style="margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:3px;">
              <span>${label}</span><strong>${Math.round(val * 100)}%</strong>
            </div>
            <div class="meter"><div class="meter-fill" style="width:${Math.round(val * 100)}%"></div></div>
          </div>
        `
          )
          .join("")}

        <div style="margin-top:14px;">
          <div style="font-size:0.78rem;color:var(--text-muted);margin-bottom:6px;">Rubric Concepts</div>
          <div class="tag-list">
            ${(bd.matched_concepts || []).map((c) => `<span class="tag tag-hit">+ ${escapeHtml(c)}</span>`).join("")}
            ${(bd.missing_concepts || []).map((c) => `<span class="tag tag-miss">- ${escapeHtml(c)}</span>`).join("")}
          </div>
        </div>
      `;
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  container.querySelector("#nlp-sandbox-form").onsubmit = (e) => {
    e.preventDefault();
    runPreview();
  };
  runPreview();
}
