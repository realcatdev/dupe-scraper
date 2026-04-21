const state = {
  busy: false,
  apiKey: localStorage.getItem("dupe_api_key") || "",
  apiBaseUrl: localStorage.getItem("dupe_api_base_url") || "https://dupe.fi",
};

const els = {
  apiBaseUrl: document.querySelector("#apiBaseUrl"),
  apiKey: document.querySelector("#apiKey"),
  saveApiKey: document.querySelector("#saveApiKey"),
  clearApiKey: document.querySelector("#clearApiKey"),
  scan: document.querySelector("#scan"),
  scanRefresh: document.querySelector("#scanRefresh"),
  baseline: document.querySelector("#baseline"),
  status: document.querySelector("#status"),
  threshold: document.querySelector("#threshold"),
  minProfit: document.querySelector("#minProfit"),
  filters: document.querySelector("#filters"),
  learned: document.querySelector("#learned"),
  dealCount: document.querySelector("#dealCount"),
  bestProfit: document.querySelector("#bestProfit"),
  bestDiscount: document.querySelector("#bestDiscount"),
  deals: document.querySelector("#deals"),
  message: document.querySelector("#message"),
};

function money(value) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function pct(value) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function setBusy(isBusy, label = "Working") {
  state.busy = isBusy;
  els.scan.disabled = isBusy;
  els.scanRefresh.disabled = isBusy;
  els.baseline.disabled = isBusy;
  els.status.textContent = isBusy ? label : "Ready";
  els.status.className = isBusy ? "status" : "status ok";
}

function setError(message) {
  els.status.textContent = "Needs attention";
  els.status.className = "status error";
  els.message.textContent = message;
}

function applyConfig(payload) {
  if (!payload.config) return;
  const config = payload.config;
  els.threshold.textContent = pct((1 - Number(config.deal_threshold || 0)) * 100);
  els.minProfit.textContent = money(config.min_profit_usdc);
  els.filters.textContent = (config.item_filters || []).join(", ") || "all";
  els.learned.textContent = String(payload.learned_prices ?? 0);
}

function renderDeals(deals) {
  els.dealCount.textContent = String(deals.length);
  const bestProfit = deals.reduce((best, deal) => Math.max(best, deal.expected_profit || 0), 0);
  const bestDiscount = deals.reduce((best, deal) => Math.max(best, deal.discount_percent || 0), 0);
  els.bestProfit.textContent = money(bestProfit);
  els.bestDiscount.textContent = pct(bestDiscount);

  if (!deals.length) {
    els.deals.innerHTML = `<tr><td colspan="7" class="empty">No deals match the current threshold.</td></tr>`;
    return;
  }

  els.deals.innerHTML = deals.map((deal) => {
    const floatText = deal.floatvalue == null ? "" : `float ${Number(deal.floatvalue).toFixed(6)}`;
    const instant = deal.instant_fulfill ? "instant fulfill" : "standard";
    return `
      <tr>
        <td class="item-name">
          ${escapeHtml(deal.hash_name)}
          <span class="subtle">${escapeHtml([deal.category, instant, floatText].filter(Boolean).join(" / "))}</span>
        </td>
        <td>${money(deal.price)}</td>
        <td>${money(deal.typical_price)}</td>
        <td class="profit">${money(deal.expected_profit)}</td>
        <td class="discount">${pct(deal.discount_percent)}</td>
        <td>${escapeHtml(deal.source)}</td>
        <td><span class="subtle">${escapeHtml(deal.id)}</span></td>
      </tr>
    `;
  }).join("");
}

async function getJson(path) {
  const headers = {};
  if (state.apiKey) {
    headers["x-dupe-api-key"] = state.apiKey;
  }
  if (state.apiBaseUrl) {
    headers["x-dupe-api-base-url"] = state.apiBaseUrl;
  }
  const response = await fetch(path, { cache: "no-store", headers });
  return response.json();
}

async function loadStatus() {
  const payload = await getJson("/api/status");
  if (!payload.success) {
    setError(payload.error);
    return;
  }
  applyConfig(payload);
  els.status.textContent = "Ready";
  els.status.className = "status ok";
  els.message.textContent = "Config loaded.";
}

async function scan(refresh = false) {
  if (state.busy) return;
  setBusy(true, refresh ? "Refreshing" : "Scanning");
  try {
    const payload = await getJson(`/api/scan${refresh ? "?refresh=1" : ""}`);
    if (!payload.success) {
      setBusy(false);
      setError(payload.error);
      return;
    }
    applyConfig(payload);
    renderDeals(payload.deals || []);
    els.message.textContent = payload.message || `Scan complete. ${payload.deals.length} deals found.`;
    setBusy(false);
  } catch (error) {
    setBusy(false);
    setError(error.message);
  } finally {
    if (state.busy) setBusy(false);
  }
}

async function baseline() {
  if (state.busy) return;
  setBusy(true, "Updating");
  try {
    const payload = await getJson("/api/baseline");
    if (!payload.success) {
      setBusy(false);
      setError(payload.error);
      return;
    }
    applyConfig(payload);
    els.message.textContent = payload.message;
    setBusy(false);
  } catch (error) {
    setBusy(false);
    setError(error.message);
  } finally {
    if (state.busy) setBusy(false);
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function saveApiKey() {
  state.apiKey = els.apiKey.value.trim();
  state.apiBaseUrl = normalizeBaseUrl(els.apiBaseUrl.value);
  els.apiBaseUrl.value = state.apiBaseUrl;
  localStorage.setItem("dupe_api_base_url", state.apiBaseUrl);
  if (state.apiKey) {
    localStorage.setItem("dupe_api_key", state.apiKey);
    els.message.textContent = "API settings saved in this browser.";
  } else {
    localStorage.removeItem("dupe_api_key");
    els.message.textContent = "API base saved. API key cleared.";
  }
  loadStatus();
}

function clearApiKey() {
  state.apiKey = "";
  state.apiBaseUrl = "https://dupe.fi";
  els.apiKey.value = "";
  els.apiBaseUrl.value = state.apiBaseUrl;
  localStorage.removeItem("dupe_api_key");
  localStorage.setItem("dupe_api_base_url", state.apiBaseUrl);
  els.message.textContent = "API settings reset.";
  loadStatus();
}

function normalizeBaseUrl(value) {
  const trimmed = value.trim() || "https://dupe.fi";
  return trimmed.replace(/\/+$/, "");
}

els.apiBaseUrl.value = state.apiBaseUrl;
els.apiKey.value = state.apiKey;
els.saveApiKey.addEventListener("click", saveApiKey);
els.clearApiKey.addEventListener("click", clearApiKey);
els.apiKey.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    saveApiKey();
  }
});
els.apiBaseUrl.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    saveApiKey();
  }
});
els.scan.addEventListener("click", () => scan(false));
els.scanRefresh.addEventListener("click", () => scan(true));
els.baseline.addEventListener("click", baseline);

loadStatus();
