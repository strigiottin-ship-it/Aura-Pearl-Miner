const $ = (id) => document.getElementById(id);

let mode = "pool";
let nmActive = false;
let settingsDirty = false;
let coinEndpoints = {};
let coinMeta = {};

function fmtHs(n) {
  if (typeof n === "string" && /[KkMmGgTt]?H\/s/.test(n)) return n;
  n = Number(n) || 0;
  const u = ["H/s", "KH/s", "MH/s", "GH/s", "TH/s"];
  let i = 0;
  while (n >= 1000 && i < u.length - 1) { n /= 1000; i++; }
  return `${n.toFixed(i ? 2 : 0)} ${u[i]}`;
}
function fmtUptime(sec) {
  sec = Math.max(0, Math.floor(Number(sec) || 0));
  const h = String(Math.floor(sec / 3600)).padStart(2, "0");
  const m = String(Math.floor((sec % 3600) / 60)).padStart(2, "0");
  const s = String(sec % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}
function shortAddr(a) {
  a = (a || "").trim();
  if (a.length < 14) return a || "—";
  return a.slice(0, 6) + "…" + a.slice(-4);
}
function rejectPct(acc, rej) {
  const t = (Number(acc) || 0) + (Number(rej) || 0);
  if (!t) return 0;
  return (100 * (Number(rej) || 0)) / t;
}

function setMode(m) {
  mode = m === "solo" ? "solo" : "pool";
  document.querySelectorAll("#modeSeg button").forEach((b) => {
    b.classList.toggle("on", b.dataset.mode === mode);
  });
  updateLoginPreview();
}
function setNm(on) {
  nmActive = !!on;
  document.querySelectorAll("#nmActiveSeg button").forEach((b) => {
    b.classList.toggle("on", (b.dataset.nm === "1") === nmActive);
  });
}

function fillCoinSelects(coins, current) {
  const opts = (coins || []).map(
    (c) => `<option value="${c.code}">${c.label || c.code}</option>`
  ).join("");
  ["coinSelect", "setCoin"].forEach((id) => {
    const el = $(id);
    if (!el) return;
    el.innerHTML = opts;
    if (current) el.value = current;
  });
}

function updateLoginPreview() {
  const coin = $("setCoin")?.value;
  const meta = coinMeta[coin] || {};
  const wallet = ($("setWallet")?.value || "").trim();
  const override = ($("setWorker")?.value || "").trim();
  const payout = ($("setPayout")?.value || "NATIVE").trim();
  const tag = ($("setPayoutTag")?.value || "").trim();
  if (override) {
    $("setLoginPreview").value = override;
    return;
  }
  const tpl = mode === "solo" ? (meta.solo_login || "") : (meta.pool_login || "");
  let preview = tpl.replace("{address}", wallet || "ADDRESS");
  if (payout && payout.toUpperCase() !== "NATIVE" && wallet) {
    preview = tag ? `${payout}:${wallet}:${tag}.aura` : `${payout}:${wallet}.aura`;
  }
  $("setLoginPreview").value = preview || "—";
  $("setAlgo").value = meta.algo || "—";
  $("setPoolMiner").value = meta.pool_miner || "—";
  if (!$("setPass").value && meta.password) $("setPass").placeholder = meta.password;
}

function applySettingsForm(s) {
  if (!s) return;
  setMode(s.mode || "pool");
  if (s.coin) {
    if ($("setCoin")) $("setCoin").value = s.coin;
    if ($("coinSelect")) $("coinSelect").value = s.coin;
  }
  $("setHost").value = s.host || "";
  $("setPort").value = s.port || "";
  $("setWallet").value = s.wallet || "";
  $("setWorker").value = s.worker_name || "";
  $("setPass").value = s.pool_password || "";
  $("setPayout").value = s.payout || "NATIVE";
  $("setPayoutTag").value = s.payout_tag || "";
  $("setPayoutTarget").value = s.payout_target || "";
  $("setAsic").value = s.asic_ips || "";
  $("setSubnet").value = s.extra_subnet || "";
  $("setNmHost").value = s.nm_host || "";
  $("setNmHs").value = s.nm_hashrate || "";
  $("setNmWifi").value = s.nm_wifi || "";
  setNm(!!s.nm_active);
  updateLoginPreview();
  settingsDirty = false;
}

function fillEndpointFromCoin() {
  const coin = $("setCoin").value;
  const ep = coinEndpoints[coin];
  if (!ep) return;
  const pair = mode === "solo" ? ep.solo : ep.pool;
  if (pair && pair[0]) {
    $("setHost").value = pair[0];
    $("setPort").value = String(pair[1] || "");
  }
  const meta = coinMeta[coin] || {};
  if (meta.password && !$("setPass").value) $("setPass").value = meta.password;
  updateLoginPreview();
}

function renderWorkers(list) {
  const tb = document.querySelector("#workersTable tbody");
  if (!tb) return;
  if (!list || !list.length) {
    tb.innerHTML = `<tr><td colspan="8" style="color:var(--muted)">Nema workera.</td></tr>`;
    return;
  }
  tb.innerHTML = list.map((w) => {
    const on = !!w.active;
    return `<tr>
      <td>${w.name || "—"}</td>
      <td>${w.type || "—"}</td>
      <td>${w.algo || "—"}</td>
      <td>${w.hashrate || "—"}</td>
      <td>${w.temp != null ? w.temp + "°C" : "—"}</td>
      <td>${w.util != null ? w.util + "%" : "—"}</td>
      <td>${w.power != null ? w.power + " W" : "—"}</td>
      <td><span class="pill ${on ? "on" : "off"}">${on ? "● Running" : "○ Idle"}</span></td>
    </tr>`;
  }).join("");
}


function renderWalletGrids(st) {
  const wg = $("walletsGrid");
  const dg = $("withdrawGrid");
  if (!wg || !dg) return;
  const wallets = (st.settings && st.settings.wallets) || st.wallets || {};
  const withdraw = (st.settings && st.settings.withdraw_addresses) || {};
  const meta = st.coin_meta || {};
  const order = Object.keys(wallets).length ? Object.keys(wallets) : ["BTC","BCH","PRL"];
  wg.innerHTML = order.map((code) => {
    const hint = (meta[code] && meta[code].address_hint) || "";
    const val = wallets[code] || "";
    return `<div class="field full">
      <label>${code}${hint ? " — " + hint : ""}</label>
      <input class="wallet-input" data-coin="${code}" spellcheck="false" value="${String(val).replace(/"/g, "&quot;")}" />
    </div>`;
  }).join("");
  const wOrder = Object.keys(withdraw).length ? Object.keys(withdraw) : ["BTC","BCH","PRL","XRP","XMR"];
  dg.innerHTML = wOrder.map((code) => {
    const val = withdraw[code] || "";
    return `<div class="field full">
      <label>Withdraw ${code}</label>
      <input class="withdraw-input" data-coin="${code}" spellcheck="false" value="${String(val).replace(/"/g, "&quot;")}" />
    </div>`;
  }).join("");
  wg.querySelectorAll("input").forEach((el) => {
    el.addEventListener("input", () => { settingsDirty = true; });
  });
  dg.querySelectorAll("input").forEach((el) => {
    el.addEventListener("input", () => { settingsDirty = true; });
  });
}

function collectWallets() {
  const out = {};
  document.querySelectorAll(".wallet-input").forEach((el) => {
    out[el.dataset.coin] = el.value.trim();
  });
  return out;
}
function collectWithdraw() {
  const out = {};
  document.querySelectorAll(".withdraw-input").forEach((el) => {
    out[el.dataset.coin] = el.value.trim();
  });
  return out;
}

function applyState(st) {
  if (!st) return;
  if (st.coins) fillCoinSelects(st.coins, st.coin);
  if (st.endpoints) coinEndpoints = st.endpoints;
  if (st.coin_meta) coinMeta = st.coin_meta;

  const acc = st.accepted ?? 0;
  const rej = st.rejected ?? 0;
  const rp = rejectPct(acc, rej);

  $("hashrate").textContent = fmtHs(st.hashrate_s != null ? st.hashrate_s : st.hashrate);
  $("peak").textContent = "Peak " + fmtHs(st.peak);
  $("shares").textContent = String(acc);
  $("reject").textContent = `Rejected ${rej} · ${rp.toFixed(1)}%`;
  $("uptime").textContent = fmtUptime(st.uptime);
  $("statusLine").textContent = st.running ? "Mining" : (st.status || "Ready");
  $("walletShort").textContent = shortAddr(st.wallet);
  $("poolLine").textContent = `${st.host || "—"}:${st.port || ""} · ${st.mode || "pool"}`;
  $("sessionLine").textContent = st.session_line || "—";
  $("engineSub").textContent = `${st.engine || "GPU"} · ${st.mode || "pool"} · ${st.algo || ""} · ${st.coin || ""}`;
  $("engineTitle").textContent = st.running ? "Mining in progress." : "Ready to mine.";
  $("connLabel").textContent = st.running ? "Mining" : "Connected";
  $("log").textContent = (st.log || []).slice(-40).join("\n");

  const btn = $("btnStart");
  btn.textContent = st.running ? "STOP" : "START";
  btn.classList.toggle("stop", !!st.running);

  $("sHash").textContent = fmtHs(st.hashrate_s != null ? st.hashrate_s : st.hashrate);
  $("sPeak").textContent = "Peak " + fmtHs(st.peak);
  $("sAcc").textContent = String(acc);
  $("sRej").textContent = "Rejected " + String(rej);
  $("sRejPct").textContent = rp.toFixed(1) + "%";
  $("sTotal").textContent = "Total shares " + String(st.total_shares ?? acc + rej);
  $("sUp").textContent = fmtUptime(st.uptime);
  $("sMode").textContent = `${st.mode || "pool"} · ${st.coin || ""}`;
  $("sAlgo").textContent = st.algo || "—";
  $("sEng").textContent = st.engine || "—";
  $("sGpu").textContent = st.gpu_name || "—";
  $("sGpuDet").textContent = st.gpu_detail || "—";
  $("sSession").textContent = st.session_line || "—";
  $("sHashes").textContent = st.hashes_line || "";
  $("sByCoin").textContent = st.session_by_coin || "";
  $("sLog").textContent = (st.log || []).slice(-80).join("\n");

  renderWorkers(st.workers || []);
  $("workerConn").textContent = st.worker_conn || "—";

  if (!settingsDirty && st.settings) applySettingsForm(st.settings);
  
}

async function api(name, ...args) {
  if (!window.pywebview || !window.pywebview.api) return null;
  return await window.pywebview.api[name](...args);
}
async function refresh() {
  try { applyState(await api("get_state")); } catch (e) { console.error(e); }
}

function switchTab(tab) {
  document.querySelectorAll(".nav button").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === tab);
  });
  document.querySelectorAll(".panel").forEach((p) => {
    p.classList.toggle("active", p.id === "panel-" + tab);
  });
  const titles = {
    dash: ["AURA", "High-performance mining. Real ownership."],
    workers: ["WORKERS", "GPU · ASIC · USB · temp / util / power"],
    stats: ["STATS", "Hashrate · shares · reject % · session"],
    settings: ["SETTINGS", "Pool / Solo · worker · payout · devices"],
  };
  const t = titles[tab] || titles.dash;
  $("pageTitle").textContent = t[0];
  $("pageSub").textContent = t[1];
}

document.querySelectorAll(".nav button").forEach((b) => {
  b.addEventListener("click", () => switchTab(b.dataset.tab));
});
$("btnStart").addEventListener("click", async () => { await api("toggle_mining"); await refresh(); });
$("coinSelect").addEventListener("change", async () => {
  await api("set_coin", $("coinSelect").value);
  await refresh();
});
document.querySelectorAll("#modeSeg button").forEach((b) => {
  b.addEventListener("click", () => { settingsDirty = true; setMode(b.dataset.mode); });
});
document.querySelectorAll("#nmActiveSeg button").forEach((b) => {
  b.addEventListener("click", () => { settingsDirty = true; setNm(b.dataset.nm === "1"); });
});
[
  "setHost","setPort","setWallet","setWorker","setPass","setPayout","setPayoutTag",
  "setPayoutTarget","setAsic","setSubnet","setCoin","setNmHost","setNmHs","setNmWifi"
].forEach((id) => {
  const el = $(id);
  if (!el) return;
  el.addEventListener("input", () => { settingsDirty = true; updateLoginPreview(); });
  el.addEventListener("change", () => { settingsDirty = true; updateLoginPreview(); });
});
$("btnFillEndpoint").addEventListener("click", () => { settingsDirty = true; fillEndpointFromCoin(); });
$("btnSave").addEventListener("click", async () => {
  const payload = {
    coin: $("setCoin").value,
    mode,
    host: $("setHost").value.trim(),
    port: $("setPort").value.trim(),
    wallet: $("setWallet").value.trim(),
    worker_name: $("setWorker").value.trim(),
    pool_password: $("setPass").value.trim(),
    payout: $("setPayout").value.trim() || "NATIVE",
    payout_tag: $("setPayoutTag").value.trim(),
    payout_target: $("setPayoutTarget").value.trim(),
    asic_ips: $("setAsic").value.trim(),
    extra_subnet: $("setSubnet").value.trim(),
    nerdminer: {
      host: $("setNmHost").value.trim(),
      hashrate: $("setNmHs").value.trim(),
      wifi_ssid: $("setNmWifi").value.trim(),
      ssid: $("setNmWifi").value.trim(),
      active: nmActive,
    },
  };
  $("saveMsg").textContent = "Saving…";
  const res = await api("save_settings", payload);
  $("saveMsg").textContent = (res && res.ok) ? "Saved." : ((res && res.error) || "Error");
  settingsDirty = false;
  await refresh();
});

window.addEventListener("pywebviewready", () => { refresh(); setInterval(refresh, 1500); });
setTimeout(() => { refresh(); setInterval(refresh, 1500); }, 400);

/* POVUCI modal — one window like old HashStart */
function openPovuci() {
  const m = document.getElementById("povuciModal");
  if (!m) return;
  m.hidden = false;
  m.removeAttribute("hidden");
  m.style.display = "grid";
  refreshPovuci();
}
function closePovuci(e) {
  if (e && typeof e.stopPropagation === "function") e.stopPropagation();
  if (e && typeof e.preventDefault === "function") e.preventDefault();
  const m = document.getElementById("povuciModal");
  if (!m) return;
  m.hidden = true;
  m.setAttribute("hidden", "");
  m.style.display = "none";
}
async function refreshPovuci() {
  try {
    const st = await api("get_withdraw_state");
    if (!st) return;
    const coin = document.getElementById("povuciCoin");
    const addr = document.getElementById("povuciAddr");
    const tag = document.getElementById("povuciTag");
    const bal = document.getElementById("povuciBal");
    const amount = document.getElementById("povuciAmount");
    const msg = document.getElementById("povuciMsg");
    if (st.payout && coin) coin.value = st.payout;
    if (addr) addr.value = st.address || "";
    if (tag) tag.value = st.tag || "";
    if (bal) bal.value = st.balance_text || "—";
    if (st.amount && amount) amount.value = st.amount;
    if (msg) msg.textContent = st.hint || "";
  } catch (err) {
    console.error(err);
  }
}
async function doPovuci() {
  const msg = document.getElementById("povuciMsg");
  if (msg) msg.textContent = "Saljem…";
  const res = await api("povuci", {
    payout: document.getElementById("povuciCoin").value,
    address: document.getElementById("povuciAddr").value.trim(),
    tag: document.getElementById("povuciTag").value.trim(),
    amount: document.getElementById("povuciAmount").value.trim(),
  });
  if (msg) msg.textContent = (res && res.message) || (res && res.error) || "OK";
  if (res && res.ok) await refreshPovuci();
}

document.addEventListener("click", (e) => {
  const t = e.target;
  if (!t || !t.closest) return;
  if (t.closest("#btnPovuci")) {
    openPovuci();
    return;
  }
  if (t.closest("#povuciClose")) {
    closePovuci(e);
    return;
  }
  if (t.id === "povuciModal") {
    closePovuci(e);
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closePovuci(e);
});

document.getElementById("povuciPaste")?.addEventListener("click", async () => {
  const msg = document.getElementById("povuciMsg");
  const addr = document.getElementById("povuciAddr");
  try {
    const text = await navigator.clipboard.readText();
    if (text && addr) addr.value = text.trim();
  } catch (err) {
    if (msg) msg.textContent = "Clipboard nije dostupan — zalijepi rucno (Ctrl+V).";
  }
});
document.getElementById("povuciGo")?.addEventListener("click", doPovuci);
document.getElementById("povuciOpenWeb")?.addEventListener("click", async () => {
  await api("open_unmineable", {
    payout: document.getElementById("povuciCoin").value,
    address: document.getElementById("povuciAddr").value.trim(),
  });
});
document.getElementById("povuciCoin")?.addEventListener("change", async () => {
  await api("set_payout_coin", document.getElementById("povuciCoin").value);
  await refreshPovuci();
});
