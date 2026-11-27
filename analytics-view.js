import { apiFetch, escapeHtml } from "./api.js";
import { renderBarChartSvg, renderRiskBreakdownHtml } from "./charts.js";

export async function renderAnalyticsTab(container) {
  container.innerHTML = `<div class="card">Loading analytics...</div>`;
  const data = await apiFetch("/api/analytics");
  const dist = data.score_distribution || {};

  const scoreChart = renderBarChartSvg([
    { label: "0–39%", value: dist["0-39"] || 0, color: "#ef4444" },
    { label: "40–59%", value: dist["40-59"] || 0, color: "#f59e0b" },
    { label: "60–79%", value: dist["60-79"] || 0, color: "#06b6d4" },
    { label: "80–100%", value: dist["80-100"] || 0, color: "#10b981" },
  ]);

  container.innerHTML = `
    <div class="topbar">
      <div>
        <h1 class="page-title">Academic &amp; Integrity Analytics</h1>
        <p class="page-sub">Aggregated score distributions, AI confidence consistency, and proctoring integrity telemetry.</p>
      </div>
    </div>

    <div class="grid grid-4" style="margin-bottom:20px;">
      <div class="card kpi-card">
        <span class="kpi-label">Completed Submissions</span>
        <span class="kpi-value">${data.completed_count}</span>
        <span class="kpi-foot">${data.counts.total_exams} active exams</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Mean Score</span>
        <span class="kpi-value">${data.avg_percentage}%</span>
        <span class="kpi-foot">Pass Rate: ${data.pass_rate}%</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Mean Integrity</span>
        <span class="kpi-value">${data.avg_integrity_score}%</span>
        <span class="kpi-foot">Across CV &amp; browser checks</span>
      </div>
      <div class="card kpi-card">
        <span class="kpi-label">Registered Students</span>
        <span class="kpi-value">${data.counts.total_students}</span>
        <span class="kpi-foot">${data.counts.total_faculty} faculty members</span>
      </div>
    </div>

    <div class="grid grid-2" style="margin-bottom:20px;">
      <div class="card">
        <h3 class="card-title" style="margin-bottom:10px;">Score Distribution</h3>
        ${scoreChart}
      </div>
      <div class="card">
        <h3 class="card-title" style="margin-bottom:14px;">Proctoring Risk Breakdown</h3>
        ${renderRiskBreakdownHtml(data.risk_distribution || {})}
      </div>
    </div>

    <div class="card">
      <h3 class="card-title" style="margin-bottom:12px;">Question-Wise Performance &amp; AI Calibration</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Type</th>
              <th>Question</th>
              <th>Responses</th>
              <th>Avg Score</th>
              <th>AI Confidence</th>
              <th>Overrides</th>
            </tr>
          </thead>
          <tbody>
            ${(data.question_stats || [])
              .map(
                (q) => `
              <tr>
                <td>Q${q.order_index}</td>
                <td><span class="badge badge-primary">${escapeHtml(q.question_type)}</span></td>
                <td style="max-width:420px;">${escapeHtml(q.prompt)}</td>
                <td>${q.response_count}</td>
                <td><strong>${q.avg_marks} / ${q.max_marks}</strong> (${q.avg_pct}%)</td>
                <td>${Math.round(q.avg_confidence * 100)}%</td>
                <td>${q.override_count}</td>
              </tr>
            `
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}
