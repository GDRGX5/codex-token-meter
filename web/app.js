const translations = {
  en: {
    eyebrow: "LOCAL USAGE INTELLIGENCE",
    headline: "Know where every token went.",
    subhead: "A private dashboard for local Codex Desktop and CLI sessions, with API-equivalent cost estimates by model.",
    privacy: "Localhost only · no chat content uploaded",
    filtersKicker: "REPORT CONTROLS", filtersTitle: "Choose a reporting window",
    period: "Period", today: "Today", last7: "Last 7 days", last30: "Last 30 days",
    specificDate: "Specific date", allHistory: "All local history", date: "Date",
    runReport: "Run report",
    allWarning: "All history can take longer on large Codex archives.",
    scanning: "Scanning local sessions…", scanningDetail: "Large histories may take a moment. Nothing is uploaded.",
    totalTokens: "Total tokens", apiEquivalent: "API equivalent (USD)", estimateOnly: "Estimate, not a subscription bill",
    events: "Model events", eventsHint: "Includes agent and tool-loop calls", cacheRate: "Cached input share",
    trendKicker: "DAILY TREND", dailyUsage: "Daily token usage", modelKicker: "MODEL MIX",
    usageByModel: "Usage by model", model: "Model", input: "Input", cached: "Cached",
    output: "Output", reasoning: "Reasoning", whyLarge: "Why can the total look so large?",
    whyLargeCopy: "Each model call processes the active context again. Cached prefixes still count as cached-input tokens, but use a lower API rate.",
    noData: "No data for this period", models: "models", periodLabel: "Period", source: "Source",
    scanned: "Scanned {files} files · removed {duplicates} duplicate snapshots",
    pricing: "Pricing updated {date}", failed: "Could not build the report", retry: "Check the local server and try again.",
    cachedDetail: "{cached} cached input tokens"
  },
  "zh-TW": {
    eyebrow: "本機用量分析", headline: "每一枚 token，都有跡可循。",
    subhead: "在本機統計 Codex Desktop 與 CLI 工作階段，依模型換算 API 等值成本。",
    privacy: "僅限 localhost · 不上傳聊天內容",
    filtersKicker: "報表控制", filtersTitle: "選擇統計期間",
    period: "期間", today: "今天", last7: "最近 7 天", last30: "最近 30 天",
    specificDate: "指定日期", allHistory: "全部本機紀錄", date: "日期",
    runReport: "產生報表",
    allWarning: "完整歷史在大型 Codex 紀錄庫中可能需要較長時間。",
    scanning: "正在掃描本機工作階段…", scanningDetail: "大型紀錄可能需要一些時間；資料不會上傳。",
    totalTokens: "總 token", apiEquivalent: "API 等值（USD）", estimateOnly: "僅為估算，不是訂閱帳單",
    events: "模型計數事件", eventsHint: "包含代理與工具迴圈呼叫", cacheRate: "快取輸入比例",
    trendKicker: "每日趨勢", dailyUsage: "每日 token 用量", modelKicker: "模型分布",
    usageByModel: "各模型用量", model: "模型", input: "輸入", cached: "快取",
    output: "輸出", reasoning: "推理輸出", whyLarge: "為什麼總量看起來很大？",
    whyLargeCopy: "每次模型呼叫都會重新處理目前上下文；命中快取的前綴仍計入快取輸入 token，但 API 費率較低。",
    noData: "這段期間沒有資料", models: "個模型", periodLabel: "期間", source: "來源",
    scanned: "掃描 {files} 個檔案 · 去除 {duplicates} 個重複快照",
    pricing: "價格更新日 {date}", failed: "無法產生報表", retry: "請檢查本機伺服器後再試一次。",
    cachedDetail: "{cached} 個快取輸入 token"
  }
};

const state = {
  lang: localStorage.getItem("codex-token-meter-lang") || (navigator.language.startsWith("zh") ? "zh-TW" : "en"),
  report: null
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const text = (key, values = {}) => {
  let value = translations[state.lang][key] || key;
  Object.entries(values).forEach(([name, replacement]) => value = value.replace(`{${name}}`, replacement));
  return value;
};

function applyLanguage() {
  document.documentElement.lang = state.lang;
  document.title = state.lang === "zh-TW" ? "Codex Token Meter｜本機用量" : "Codex Token Meter · Local usage";
  $$('[data-i18n]').forEach((element) => {
    const key = element.dataset.i18n;
    if (translations[state.lang][key]) element.textContent = translations[state.lang][key];
  });
  $$('[data-lang]').forEach((button) => button.classList.toggle("active", button.dataset.lang === state.lang));
  if (state.report) renderReport(state.report);
}

function localeName() { return state.lang === "zh-TW" ? "zh-TW" : "en-US"; }
function fullNumber(value) { return new Intl.NumberFormat(localeName()).format(value || 0); }
function compactNumber(value) {
  return new Intl.NumberFormat(localeName(), { notation: "compact", maximumFractionDigits: 2 }).format(value || 0);
}
function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[character]);
}
function money(aggregate) {
  if (aggregate.requests && aggregate.unpriced_requests === aggregate.requests) return "—";
  const marker = aggregate.unpriced_requests ? "*" : "";
  const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 4 }).format(aggregate.known_cost_usd || 0);
  return `${usd}${marker}`;
}

function setLoading(isLoading) {
  $("#status-panel").classList.toggle("is-hidden", !isLoading);
  $("#status-panel").classList.remove("error");
  $("#dashboard").classList.toggle("is-hidden", isLoading || !state.report);
}

function showError(message) {
  const panel = $("#status-panel");
  panel.classList.remove("is-hidden");
  panel.classList.add("error");
  panel.querySelector(".spinner").classList.add("is-hidden");
  $("#status-title").textContent = text("failed");
  $("#status-copy").textContent = message || text("retry");
}

function reportQuery() {
  const params = new URLSearchParams({ lang: state.lang });
  const period = $("#period-select").value;
  if (period === "all") params.set("all", "1");
  else if (period === "date") params.set("date", $("#date-input").value);
  else params.set("days", period === "today" ? "1" : period);
  return params;
}

async function loadReport() {
  setLoading(true);
  $("#status-title").textContent = text("scanning");
  $("#status-copy").textContent = text("scanningDetail");
  $("#status-panel .spinner").classList.remove("is-hidden");
  try {
    const response = await fetch(`/api/report?${reportQuery()}`);
    const payload = await response.json();
    if (!response.ok || payload.error) throw new Error(payload.error || response.statusText);
    state.report = payload;
    renderReport(payload);
    setLoading(false);
  } catch (error) {
    showError(error.message);
  }
}

function renderReport(report) {
  const total = report.total;
  $("#period-label").textContent = `${text("periodLabel")}: ${report.period}`;
  $("#source-label").textContent = `${text("source")}: ${report.source}`;
  $("#metric-tokens").textContent = compactNumber(total.total_tokens);
  $("#metric-tokens-full").textContent = fullNumber(total.total_tokens);
  $("#metric-cost").textContent = money(total);
  $("#metric-events").textContent = fullNumber(total.requests);
  const cacheRate = total.input_tokens ? total.cached_input_tokens / total.input_tokens * 100 : 0;
  $("#metric-cache").textContent = `${cacheRate.toFixed(1)}%`;
  $("#metric-cache-detail").textContent = text("cachedDetail", { cached: fullNumber(total.cached_input_tokens) });

  const dailyEntries = Object.entries(report.daily).sort(([a], [b]) => a.localeCompare(b));
  const maxTokens = Math.max(1, ...dailyEntries.map(([, value]) => value.total_tokens));
  $("#daily-chart").innerHTML = dailyEntries.length ? dailyEntries.map(([day, value]) => `
    <div class="bar-row">
      <span class="bar-date">${escapeHtml(day)}</span>
      <div class="bar-track" title="${fullNumber(value.total_tokens)}"><div class="bar-fill" style="width:${Math.max(0.4, value.total_tokens / maxTokens * 100)}%"></div></div>
      <span class="bar-value">${compactNumber(value.total_tokens)}</span>
    </div>`).join("") : `<p class="empty-state">${text("noData")}</p>`;

  const models = Object.entries(report.models).sort(([, a], [, b]) => b.total_tokens - a.total_tokens);
  $("#model-count").textContent = `${models.length} ${text("models")}`;
  $("#model-table").innerHTML = models.length ? models.map(([model, value]) => `
    <tr>
      <td>${escapeHtml(model)}</td><td>${fullNumber(value.requests)}</td><td>${fullNumber(value.input_tokens)}</td>
      <td>${fullNumber(value.cached_input_tokens)}</td><td>${fullNumber(value.output_tokens)}</td>
      <td>${fullNumber(value.reasoning_output_tokens)}</td><td>${fullNumber(value.total_tokens)}</td>
      <td class="${value.unpriced_requests === value.requests ? "unknown-cost" : ""}">${money(value)}</td>
    </tr>`).join("") : `<tr><td colspan="8" class="empty-state">${text("noData")}</td></tr>`;

  $("#diagnostics-label").textContent = text("scanned", {
    files: fullNumber(report.diagnostics.files), duplicates: fullNumber(report.diagnostics.duplicate_snapshots)
  });
  $("#pricing-label").textContent = text("pricing", { date: report.pricing_updated });
}

function updatePeriodControls() {
  const period = $("#period-select").value;
  $("#date-field").classList.toggle("is-hidden", period !== "date");
  $("#range-warning").classList.toggle("is-hidden", period !== "all");
}

document.addEventListener("DOMContentLoaded", () => {
  $("#date-input").value = new Date().toLocaleDateString("en-CA");
  $$('[data-lang]').forEach((button) => button.addEventListener("click", () => {
    state.lang = button.dataset.lang;
    localStorage.setItem("codex-token-meter-lang", state.lang);
    applyLanguage();
  }));
  $("#period-select").addEventListener("change", updatePeriodControls);
  $("#report-form").addEventListener("submit", (event) => { event.preventDefault(); loadReport(); });
  applyLanguage();
  updatePeriodControls();
  loadReport();
});
