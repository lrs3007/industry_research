const state = {
  payload: null,
  factorMode: "score",
  category: "all",
  platform: "all",
};

const els = {
  refreshButton: document.querySelector("#refreshButton"),
  sourceDot: document.querySelector("#sourceDot"),
  sourceMode: document.querySelector("#sourceMode"),
  lastUpdate: document.querySelector("#lastUpdate"),
  marketCount: document.querySelector("#marketCount"),
  platformCount: document.querySelector("#platformCount"),
  confidenceAverage: document.querySelector("#confidenceAverage"),
  riskState: document.querySelector("#riskState"),
  factorGrid: document.querySelector("#factorGrid"),
  assetList: document.querySelector("#assetList"),
  heatmap: document.querySelector("#heatmap"),
  eventRows: document.querySelector("#eventRows"),
  categoryFilter: document.querySelector("#categoryFilter"),
  platformFilter: document.querySelector("#platformFilter"),
  errorBanner: document.querySelector("#errorBanner"),
};

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  loadDashboard();
});

function bindEvents() {
  els.refreshButton.addEventListener("click", () => refreshDashboard());
  document.querySelectorAll("[data-factor-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      state.factorMode = button.dataset.factorMode;
      document.querySelectorAll("[data-factor-mode]").forEach((item) => item.classList.toggle("active", item === button));
      renderFactors();
    });
  });
  els.categoryFilter.addEventListener("change", () => {
    state.category = els.categoryFilter.value;
    renderEvents();
  });
  els.platformFilter.addEventListener("change", () => {
    state.platform = els.platformFilter.value;
    renderEvents();
  });
}

async function loadDashboard() {
  const payload = await requestJson("/api/dashboard");
  state.payload = payload;
  render();
}

async function refreshDashboard() {
  els.refreshButton.disabled = true;
  els.refreshButton.innerHTML = '<span class="button-icon">↻</span>刷新中';
  try {
    const payload = await requestJson("/api/refresh?limit=160");
    state.payload = payload;
    render();
  } finally {
    els.refreshButton.disabled = false;
    els.refreshButton.innerHTML = '<span class="button-icon">↻</span>刷新数据';
  }
}

async function requestJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

function render() {
  if (!state.payload) return;
  renderSource();
  renderSummary();
  renderFilters();
  renderFactors();
  renderAssets();
  renderHeatmap();
  renderEvents();
}

function renderSource() {
  const payload = state.payload;
  const isDemo = payload.status === "demo";
  els.sourceDot.className = `source-dot ${isDemo ? "demo" : "live"}`;
  els.sourceMode.textContent = isDemo ? "Demo fallback" : "Live data";
  els.lastUpdate.textContent = payload.generatedAt ? formatDate(payload.generatedAt) : "未采集";
  if (payload.errors && payload.errors.length) {
    els.errorBanner.hidden = false;
    els.errorBanner.textContent = payload.errors.join(" | ");
  } else {
    els.errorBanner.hidden = true;
    els.errorBanner.textContent = "";
  }
}

function renderSummary() {
  const summary = state.payload.summary;
  els.marketCount.textContent = formatInteger(summary.marketCount);
  els.platformCount.textContent = summary.platforms.length;
  els.confidenceAverage.textContent = formatPercent(summary.averageConfidence);
  const geo = state.payload.factors.find((item) => item.key === "geopolitical_risk")?.score || 0;
  const inflation = state.payload.factors.find((item) => item.key === "inflation_risk")?.score || 0;
  const policy = state.payload.factors.find((item) => item.key === "policy_uncertainty")?.score || 0;
  const stress = (geo + inflation + policy) / 3;
  els.riskState.textContent = stress > 0.18 ? "偏紧张" : stress < -0.12 ? "缓和" : "中性";
}

function renderFilters() {
  const events = state.payload.topEvents;
  const categories = unique(events.map((item) => item.categoryLabel));
  const platforms = unique(events.map((item) => item.platform));
  fillSelect(els.categoryFilter, categories, state.category);
  fillSelect(els.platformFilter, platforms, state.platform);
}

function renderFactors() {
  const mode = state.factorMode;
  els.factorGrid.innerHTML = state.payload.factors
    .map((factor) => {
      const value = mode === "momentum" ? factor.momentum : factor.score;
      const label = mode === "momentum" ? formatSignedPercent(value) : formatSignedScore(value);
      const tone = value > 0.04 ? "good" : value < -0.04 ? "bad" : "neutral";
      const width = Math.min(100, Math.max(3, Math.abs(value) * 100));
      return `
        <article class="factor-card">
          <div class="factor-top">
            <strong>${escapeHtml(factor.label)}</strong>
            <span class="badge ${tone}">${label}</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill ${tone}" style="width: ${width}%"></div>
          </div>
          <div class="factor-meta">
            <span>事件 ${factor.eventCount}</span>
            <span>置信 ${formatPercent(factor.confidence)}</span>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderAssets() {
  els.assetList.innerHTML = state.payload.assetImpacts
    .map((asset) => {
      const positive = asset.score >= 0;
      const width = Math.abs(asset.score) * 50;
      const notes = asset.contributors.length ? asset.contributors.join(" / ") : "暂无主导事件";
      return `
        <article class="asset-row">
          <div class="asset-main">
            <div class="asset-name">${escapeHtml(asset.asset)}</div>
            <div class="score-value ${positive ? "positive" : "negative"}">${formatSignedScore(asset.score)}</div>
            <div class="mini-track">
              <div class="mini-fill ${positive ? "" : "negative"}" style="width: ${width}%"></div>
            </div>
          </div>
          <div class="asset-notes">${escapeHtml(notes)}</div>
        </article>
      `;
    })
    .join("");
}

function renderHeatmap() {
  const rows = state.payload.heatmap.slice(0, 10);
  els.heatmap.innerHTML = rows
    .map((row) => {
      const cells = row.cells.slice(0, 4).map((cell) => {
        const color = heatColor(cell.score);
        return `<div class="heatmap-cell" style="background:${color}">${escapeHtml(cell.factor)} ${formatSignedScore(cell.score)}</div>`;
      });
      return `<div class="heatmap-row"><div class="heatmap-cell asset-label">${escapeHtml(row.asset)}</div>${cells.join("")}</div>`;
    })
    .join("");
}

function renderEvents() {
  const rows = state.payload.topEvents.filter((event) => {
    const categoryOk = state.category === "all" || event.categoryLabel === state.category;
    const platformOk = state.platform === "all" || event.platform === state.platform;
    return categoryOk && platformOk;
  });

  els.eventRows.innerHTML = rows
    .map((event) => {
      const title = event.url ? `<a class="event-title" href="${event.url}" target="_blank" rel="noreferrer">${escapeHtml(event.title)}</a>` : `<span class="event-title">${escapeHtml(event.title)}</span>`;
      return `
        <tr>
          <td>${title}</td>
          <td><span class="platform-pill">${escapeHtml(event.platform)}</span></td>
          <td>${escapeHtml(event.categoryLabel)}</td>
          <td class="number">${formatPercent(event.probability)}</td>
          <td class="number ${event.change24h >= 0 ? "positive" : "negative"}">${formatSignedPercent(event.change24h)}</td>
          <td class="number">${formatPercent(event.confidence)}</td>
          <td class="number">${formatCompact(event.volume)}</td>
        </tr>
      `;
    })
    .join("");
}

function fillSelect(select, values, current) {
  const valueSet = new Set(["all", ...values]);
  const nextValue = valueSet.has(current) ? current : "all";
  select.innerHTML = `<option value="all">全部</option>${values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("")}`;
  select.value = nextValue;
  if (select === els.categoryFilter) state.category = nextValue;
  if (select === els.platformFilter) state.platform = nextValue;
}

function unique(values) {
  return Array.from(new Set(values)).sort();
}

function heatColor(score) {
  const alpha = Math.min(0.85, Math.abs(score) * 0.85 + 0.08);
  if (score > 0) return `rgba(10, 143, 106, ${alpha})`;
  if (score < 0) return `rgba(196, 62, 62, ${alpha})`;
  return "#fff";
}

function formatDate(value) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatPercent(value) {
  return `${Math.round((value || 0) * 100)}%`;
}

function formatSignedPercent(value) {
  const pct = Math.round((value || 0) * 100);
  return `${pct > 0 ? "+" : ""}${pct}%`;
}

function formatSignedScore(value) {
  const score = Math.round((value || 0) * 100);
  return `${score > 0 ? "+" : ""}${score}`;
}

function formatInteger(value) {
  return new Intl.NumberFormat("zh-CN").format(value || 0);
}

function formatCompact(value) {
  return new Intl.NumberFormat("zh-CN", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value || 0);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

