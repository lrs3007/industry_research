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
  macroRefreshButton: document.querySelector("#macroRefreshButton"),
  macroStatus: document.querySelector("#macroStatus"),
  macroSummary: document.querySelector("#macroSummary"),
  macroGroups: document.querySelector("#macroGroups"),
  assetList: document.querySelector("#assetList"),
  heatmap: document.querySelector("#heatmap"),
  eventRows: document.querySelector("#eventRows"),
  categoryFilter: document.querySelector("#categoryFilter"),
  platformFilter: document.querySelector("#platformFilter"),
  errorBanner: document.querySelector("#errorBanner"),
};

const PLATFORM_LABELS = {
  demo: "演示数据",
  test: "测试数据",
  polymarket: "Polymarket",
  kalshi: "Kalshi",
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
  els.macroRefreshButton.addEventListener("click", () => refreshMacroDashboard());
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

async function refreshMacroDashboard() {
  els.macroRefreshButton.disabled = true;
  els.macroRefreshButton.innerHTML = '<span class="button-icon">↻</span>刷新中';
  els.macroStatus.textContent = "正在采集免费数据源";
  try {
    const payload = await requestJson("/api/macro/refresh");
    state.payload.macroDashboard = payload.macroDashboard;
    renderMacroDashboard();
  } finally {
    els.macroRefreshButton.disabled = false;
    els.macroRefreshButton.innerHTML = '<span class="button-icon">↻</span>刷新宏观数据';
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
  renderMacroDashboard();
  renderAssets();
  renderHeatmap();
  renderEvents();
}

function renderSource() {
  const payload = state.payload;
  const isDemo = payload.status === "demo";
  els.sourceDot.className = `source-dot ${isDemo ? "demo" : "live"}`;
  els.sourceMode.textContent = isDemo ? "演示数据" : "实时数据";
  els.lastUpdate.textContent = payload.generatedAt ? formatDate(payload.generatedAt) : "未采集";
  if (payload.errors && payload.errors.length) {
    els.errorBanner.hidden = false;
    els.errorBanner.textContent = payload.errors.map(translateErrorMessage).join(" | ");
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
  fillSelect(els.platformFilter, platforms, state.platform, platformLabel);
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

function renderMacroDashboard() {
  const dashboard = state.payload.macroDashboard;
  if (!dashboard) return;

  els.macroStatus.textContent = dashboard.fetchedAt ? `${dashboard.status}：${formatDate(dashboard.fetchedAt)}` : dashboard.status || "待刷新宏观数据";
  els.macroSummary.innerHTML = [
    ["指标组", formatInteger(dashboard.summary.groupCount)],
    ["指标项", formatInteger(dashboard.summary.indicatorCount)],
    ["已接入", formatInteger(dashboard.summary.connectedCount)],
    ["频率", dashboard.summary.frequencyMix.join(" / ")],
  ]
    .map(
      ([label, value]) => `
        <article class="macro-stat">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
        </article>
      `
    )
    .join("");

  els.macroGroups.innerHTML = dashboard.groups
    .map(
      (group) => `
        <section class="macro-group">
          <div class="macro-group-head">
            <h3>${escapeHtml(group.label)}</h3>
            <p>${escapeHtml(group.description)}</p>
          </div>
          <div class="macro-indicators">
            ${group.indicators.map(renderMacroIndicator).join("")}
          </div>
        </section>
      `
    )
    .join("");
}

function renderMacroIndicator(indicator) {
  const current = indicator.current;
  const status = indicator.status || "";
  const statusTone = status === "采集失败" ? "bad" : status === "部分接入" || status.includes("偏旧") || status.includes("替代") ? "warn" : status.startsWith("已接入") ? "good" : "neutral";
  return `
    <article class="macro-card">
      <div class="macro-card-top">
        <strong>${escapeHtml(indicator.name)}</strong>
        <span class="${statusTone}">${escapeHtml(status)}</span>
      </div>
      ${current ? renderMacroCurrent(current) : renderMacroEmpty(indicator)}
      <dl>
        <div>
          <dt>频率</dt>
          <dd>${escapeHtml(indicator.frequency)}</dd>
        </div>
        <div>
          <dt>来源</dt>
          <dd>${escapeHtml(indicator.source)}</dd>
        </div>
        <div>
          <dt>观察口径</dt>
          <dd>${escapeHtml(indicator.watch)}</dd>
        </div>
        <div>
          <dt>信号用途</dt>
          <dd>${escapeHtml(indicator.signal)}</dd>
        </div>
        <div>
          <dt>关联资产</dt>
          <dd>${escapeHtml(indicator.related)}</dd>
        </div>
        <div>
          <dt>接口</dt>
          <dd>${escapeHtml(indicator.sourceApi || "待配置")}</dd>
        </div>
      </dl>
    </article>
  `;
}

function renderMacroCurrent(current) {
  const change = current.changeText ? `<small>${escapeHtml(current.changeLabel || "参考")}: ${escapeHtml(current.changeText)}</small>` : "";
  const note = current.note ? `<small>${escapeHtml(current.note)}</small>` : "";
  return `
    <div class="macro-current">
      <span>${escapeHtml(current.valueLabel || "最新值")}</span>
      <strong>${escapeHtml(current.valueText || "--")}</strong>
      <small>${escapeHtml(current.period || "最新期")}</small>
      ${change}
      ${note}
    </div>
  `;
}

function renderMacroEmpty(indicator) {
  const message = indicator.error || "点击刷新宏观数据后采集";
  return `
    <div class="macro-current empty">
      <span>最新值</span>
      <strong>--</strong>
      <small>${escapeHtml(message)}</small>
    </div>
  `;
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
      const displayTitle = event.titleZh || event.title;
      const title = event.url ? `<a class="event-title" href="${event.url}" target="_blank" rel="noreferrer">${escapeHtml(displayTitle)}</a>` : `<span class="event-title">${escapeHtml(displayTitle)}</span>`;
      return `
        <tr>
          <td>${title}</td>
          <td><span class="platform-pill">${escapeHtml(event.platformLabel || platformLabel(event.platform))}</span></td>
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

function fillSelect(select, values, current, labelFormatter = (value) => value) {
  const valueSet = new Set(["all", ...values]);
  const nextValue = valueSet.has(current) ? current : "all";
  select.innerHTML = `<option value="all">全部</option>${values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(labelFormatter(value))}</option>`).join("")}`;
  select.value = nextValue;
  if (select === els.categoryFilter) state.category = nextValue;
  if (select === els.platformFilter) state.platform = nextValue;
}

function unique(values) {
  return Array.from(new Set(values)).sort();
}

function platformLabel(value) {
  return PLATFORM_LABELS[value] || value;
}

function translateErrorMessage(message) {
  return String(message)
    .replaceAll("No live markets were collected; using latest local snapshots.", "未采集到实时市场，正在使用最近一次本地快照。")
    .replaceAll("No live markets were collected; using demo dataset.", "未采集到实时市场，正在使用演示数据集。")
    .replaceAll("polymarket:", "Polymarket 采集失败：")
    .replaceAll("kalshi:", "Kalshi 采集失败：")
    .replaceAll("Could not fetch", "无法获取");
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
