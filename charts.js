// Lightweight SVG Charts for Analytics & Result Visualization

import { escapeHtml } from "./api.js";

export function renderBarChartSvg(items, { height = 180, color = "#6366f1" } = {}) {
  const maxVal = Math.max(1, ...items.map((i) => Number(i.value || 0)));
  const width = 420;
  const padX = 24;
  const padTop = 18;
  const padBottom = 34;
  const chartH = height - padTop - padBottom;
  const slotW = (width - padX * 2) / Math.max(1, items.length);
  const barW = Math.min(46, slotW * 0.56);

  const bars = items
    .map((item, idx) => {
      const val = Number(item.value || 0);
      const barH = (val / maxVal) * chartH;
      const x = padX + idx * slotW + (slotW - barW) / 2;
      const y = padTop + (chartH - barH);
      const fill = item.color || color;
      return `
        <g>
          <rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${barH.toFixed(1)}" rx="6" fill="${fill}" opacity="0.9"></rect>
          <text x="${(x + barW / 2).toFixed(1)}" y="${(y - 5).toFixed(1)}" text-anchor="middle" fill="currentColor" font-size="11" font-weight="700">${escapeHtml(item.displayValue ?? val)}</text>
          <text x="${(x + barW / 2).toFixed(1)}" y="${height - 10}" text-anchor="middle" fill="#94a3b8" font-size="11">${escapeHtml(item.label)}</text>
        </g>
      `;
    })
    .join("");

  return `
    <svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto;display:block;">
      <line x1="${padX}" y1="${padTop + chartH}" x2="${width - padX}" y2="${padTop + chartH}" stroke="rgba(148,163,184,0.25)" stroke-width="1"/>
      ${bars}
    </svg>
  `;
}

export function renderRiskBreakdownHtml(riskDist) {
  const total = Math.max(
    1,
    (riskDist.CLEAR || 0) + (riskDist.WATCH || 0) + (riskDist.FLAGGED || 0)
  );
  const rows = [
    { label: "CLEAR (High Integrity)", val: riskDist.CLEAR || 0, color: "var(--success)" },
    { label: "WATCH (Minor Flags)", val: riskDist.WATCH || 0, color: "var(--warning)" },
    { label: "FLAGGED (Review Required)", val: riskDist.FLAGGED || 0, color: "var(--danger)" },
  ];

  return rows
    .map((r) => {
      const pct = Math.round((r.val / total) * 100);
      return `
        <div style="margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;font-size:0.84rem;margin-bottom:4px;">
            <span>${escapeHtml(r.label)}</span>
            <strong>${r.val} (${pct}%)</strong>
          </div>
          <div class="meter">
            <div class="meter-fill" style="width:${pct}%;background:${r.color};"></div>
          </div>
        </div>
      `;
    })
    .join("");
}
