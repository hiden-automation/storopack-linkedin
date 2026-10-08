"use strict";

// Mesmas regras de config.py
const POST_WEEKDAYS = [1, 3, 5]; // segunda, quarta, sexta (0 = domingo)
const POST_WINDOW_END = 12; // publica entre 9h e 12h (Brasília)
const REFILL_MAX_ACCEPTED = 3;
const OVERRIDE_TTL_MS = 30 * 60 * 1000;
const POLL_MS = 20 * 1000;

const STATUS_LABEL = {
  pending: "Pendente",
  accepted: "Aceito",
  rejected: "Recusado",
  posted: "Publicado",
  failed: "Falhou",
  generating: "Gerando",
};

const TABS = [
  { key: "pending", label: "Pendentes" },
  { key: "accepted", label: "Fila (aceitos)" },
  { key: "posted", label: "Publicados" },
  { key: "rejected", label: "Recusados" },
  { key: "failed", label: "Com falha", hideWhenEmpty: true },
  { key: "all", label: "Todos" },
];

const $ = (sel) => document.querySelector(sel);

let posts = [];
let state = {};
let currentTab = "pending";
let pollTimer = null;

// ---------- armazenamento local (só conveniências deste navegador) ----------
function lsGet(key, fallback) {
  try {
    const v = localStorage.getItem(key);
    return v === null ? fallback : JSON.parse(v);
  } catch {
    return fallback;
  }
}
function lsSet(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* sem armazenamento: segue sem persistir */
  }
}

function detectRepo() {
  const host = location.hostname;
  if (host.endsWith(".github.io")) {
    const owner = host.split(".")[0];
    const repo = location.pathname.split("/").filter(Boolean)[0] || `${owner}.github.io`;
    return `${owner}/${repo}`;
  }
  return "";
}

const settings = () => ({
  repo: lsGet("storobot.repo", "") || detectRepo(),
  token: lsGet("storobot.token", ""),
});

// Mudanças feitas aqui que ainda não chegaram ao posts.json publicado
const getOverrides = () => lsGet("storobot.overrides", {});
const setOverrides = (o) => lsSet("storobot.overrides", o);

function effectiveStatus(post) {
  const o = getOverrides()[post.id];
  if (o && Date.now() - o.at < OVERRIDE_TTL_MS && o.status !== post.status) {
    return { status: o.status, syncing: true };
  }
  return { status: post.status, syncing: false };
}

function pruneOverrides() {
  const overrides = getOverrides();
  const byId = Object.fromEntries(posts.map((p) => [p.id, p]));
  for (const [id, o] of Object.entries(overrides)) {
    const done = byId[id] && byId[id].status === o.status;
    if (done || Date.now() - o.at > OVERRIDE_TTL_MS) delete overrides[id];
  }
  setOverrides(overrides);
  return Object.keys(overrides).length;
}

// ---------- dados ----------
async function load() {
  const bust = `?t=${Date.now()}`;
  const [p, s] = await Promise.all([
    fetch(`data/posts.json${bust}`).then((r) => (r.ok ? r.json() : [])).catch(() => []),
    fetch(`data/state.json${bust}`).then((r) => (r.ok ? r.json() : {})).catch(() => ({})),
  ]);
  posts = p;
  state = s;
  const pendingSync = pruneOverrides();
  render();
  clearTimeout(pollTimer);
  if (pendingSync) pollTimer = setTimeout(load, POLL_MS);
}

// ---------- ações ----------
async function dispatchWorkflow(workflow, inputs) {
  const { repo, token } = settings();
  const res = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/${workflow}/dispatches`, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token}`,
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify({ ref: "main", inputs }),
  });
  if (res.status !== 204) {
    const body = await res.json().catch(() => ({}));
    throw new Error(`${res.status} ${body.message || res.statusText}`);
  }
}

function requireAccess() {
  const { repo, token } = settings();
  if (repo && token) return true;
  toast("Configure o acesso ao GitHub primeiro.", true);
  openSettings();
  return false;
}

async function setStatus(post, status, buttons) {
  if (!requireAccess()) return;
  buttons.forEach((b) => (b.disabled = true));
  try {
    await dispatchWorkflow("set-status.yml", { post_id: post.id, status });
    const overrides = getOverrides();
    overrides[post.id] = { status, at: Date.now() };
    setOverrides(overrides);
    toast(`Post ${status === "accepted" ? "aceito" : status === "rejected" ? "recusado" : "atualizado"}. Sincronizando com o repositório…`);
    render();
    clearTimeout(pollTimer);
    pollTimer = setTimeout(load, POLL_MS);
  } catch (err) {
    toast(`Não foi possível alterar o status: ${err.message}`, true);
    buttons.forEach((b) => (b.disabled = false));
  }
}

// ---------- PWA: instalação ----------
const isStandalone = () =>
  matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent) ||
  (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

let installPrompt = null;

function setupInstall() {
  const btn = $("#install-btn");
  if (isStandalone()) return;
  if (isIOS()) btn.hidden = false;
  addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    installPrompt = e;
    btn.hidden = false;
  });
  addEventListener("appinstalled", () => {
    btn.hidden = true;
    toast("App instalado!");
  });
  btn.addEventListener("click", async () => {
    if (installPrompt) {
      installPrompt.prompt();
      await installPrompt.userChoice;
      installPrompt = null;
      btn.hidden = true;
    } else if (isIOS()) {
      $("#ios-install").showModal();
    }
  });
}

// ---------- PWA: notificações ----------
const pushSupported = () => "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;

function urlBase64ToUint8Array(base64) {
  const padded = (base64 + "=".repeat((4 - (base64.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
}

async function subscribeDevice() {
  const reg = await navigator.serviceWorker.ready;
  const sub =
    (await reg.pushManager.getSubscription()) ||
    (await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(window.STOROBOT_CONFIG.vapidPublicKey),
    }));
  await dispatchWorkflow("subscribe.yml", { subscription: JSON.stringify(sub) });
  lsSet("storobot.pushRegistered", sub.endpoint);
}

async function refreshNotifyButton() {
  const btn = $("#notify-btn");
  if (!pushSupported()) {
    // No iPhone o push só existe com o app instalado na Tela de Início
    btn.hidden = !(isIOS() && !isStandalone());
    return;
  }
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.getSubscription();
  const registered = sub && lsGet("storobot.pushRegistered", "") === sub.endpoint;
  if (Notification.permission === "granted" && !registered && settings().token) {
    // Autorreparo: o celular trocou/cancelou a inscrição (reinstalação, limpeza de dados etc.).
    // Como a permissão já foi dada, registra de novo em silêncio.
    try {
      await subscribeDevice();
      btn.hidden = true;
      return;
    } catch (err) {
      console.warn("Reinscrição automática falhou:", err);
    }
  }
  // Some depois de ativado: inscrição existe, permissão dada e já registrada no repositório
  btn.hidden = Boolean(registered && Notification.permission === "granted");
}

async function enableNotifications() {
  if (!pushSupported()) {
    $("#ios-install").showModal();
    return;
  }
  if (Notification.permission === "denied") {
    toast("As notificações estão bloqueadas. Libere nas configurações do navegador.", true);
    return;
  }
  if (!requireAccess()) return;
  const btn = $("#notify-btn");
  btn.disabled = true;
  try {
    if ((await Notification.requestPermission()) !== "granted") {
      toast("Permissão de notificação não concedida.", true);
      return;
    }
    await subscribeDevice();
    toast("Notificações ativadas! Uma notificação de teste chega em cerca de 1 minuto.");
  } catch (err) {
    toast(`Não foi possível ativar as notificações: ${err.message}`, true);
  } finally {
    btn.disabled = false;
    refreshNotifyButton();
  }
}

function setupPwa() {
  setupInstall();
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch((err) => console.warn("SW:", err));
  }
  refreshNotifyButton();
  $("#notify-btn").addEventListener("click", enableNotifications);
}

// ---------- renderização ----------
const fmtDate = (d) =>
  d.toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
const addDays = (iso, days) => new Date(new Date(iso).getTime() + days * 86400000);

// Mesma regra do post.py: seg/qua/sex por volta das 10h, no máximo um post por dia (Brasília)
function brtDate(d) {
  const p = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
  return new Date(`${p}T12:00:00-03:00`);
}
function nextPostLabel(lastIso) {
  const today = brtDate(new Date());
  const hour = Number(new Intl.DateTimeFormat("en-US", { timeZone: "America/Sao_Paulo", hour: "numeric", hourCycle: "h23" }).format(new Date()));
  const postedToday = lastIso && brtDate(new Date(lastIso)).getTime() === today.getTime();
  let day = today;
  if (postedToday || hour >= POST_WINDOW_END) day = addDays(today.toISOString(), 1);
  while (!POST_WEEKDAYS.includes(day.getUTCDay())) day = addDays(day.toISOString(), 1);
  const label = day.getTime() === today.getTime() ? "Hoje" : day.toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit", month: "short" });
  return `${label}, 10h`;
}

function queue() {
  return posts
    .filter((p) => effectiveStatus(p).status === "accepted")
    .sort((a, b) => a.cycle - b.cycle || a.order - b.order);
}

function renderSummary() {
  const q = queue();
  const pending = posts.filter((p) => effectiveStatus(p).status === "pending").length;
  const nextPost = q.length ? nextPostLabel(state.last_post_at) : "0";
  const generating = state.generation_status === "in_progress" || posts.some((p) => p.status === "generating");
  $("#next-cycle").textContent = generating
    ? "Gerando novos posts agora…"
    : q.length <= REFILL_MAX_ACCEPTED && pending === 0
      ? "Novos posts serão gerados em instantes."
      : `Novos posts são gerados quando restarem ${REFILL_MAX_ACCEPTED} ou menos na fila e nenhum aguardando aprovação.`;
  const stats = [
    ["Aguardando aprovação", pending],
    ["Na fila para publicar", q.length],
    ["Próxima publicação", nextPost],
  ];
  $("#summary").innerHTML = stats
    .map(([l, v]) => `<div class="stat"><div class="label">${l}</div><div class="value">${esc(String(v))}</div></div>`)
    .join("");
}

function renderTabs() {
  const count = (key) =>
    key === "all" ? posts.length : posts.filter((p) => effectiveStatus(p).status === key).length;
  $("#tabs").innerHTML = TABS.filter((t) => !t.hideWhenEmpty || count(t.key))
    .map(
      (t) =>
        `<button type="button" class="tab" data-tab="${t.key}" aria-pressed="${t.key === currentTab}">${t.label}<span class="count">${count(t.key)}</span></button>`,
    )
    .join("");
}

function cardHtml(post, queuePos) {
  const { status, syncing } = effectiveStatus(post);
  const img = post.image_path
    ? `<img src="${esc(post.image_path)}" alt="${esc(post.title || "")}" loading="lazy">`
    : `<div class="noimg">${post.status === "generating" ? "Imagem sendo gerada…" : "Sem imagem"}</div>`;
  const tags = (post.hashtags || []).map((h) => `#${h}`).join(" ");
  const when = post.posted_at
    ? `Publicado em ${fmtDate(new Date(post.posted_at))}`
    : queuePos
      ? `${queuePos}º na fila`
      : `Ciclo ${post.cycle} · #${post.order}`;
  const badge = syncing
    ? `<span class="badge syncing">${STATUS_LABEL[status]} · sincronizando</span>`
    : `<span class="badge ${status}">${STATUS_LABEL[status] || status}</span>`;

  const buttons = [];
  if (status === "pending" || status === "rejected") buttons.push(`<button type="button" class="accept" data-status="accepted">Aceitar</button>`);
  if (status === "pending" || status === "accepted") buttons.push(`<button type="button" class="reject" data-status="rejected">Recusar</button>`);
  const canAct = post.image_path && post.caption && ["pending", "accepted", "rejected"].includes(post.status);

  return `
    <article class="card" data-id="${esc(post.id)}">
      ${img}
      <div class="card-body">
        <div class="meta"><span>${when}</span>${badge}</div>
        <h3>${esc(post.title || post.topic)}</h3>
        <p class="topic">${esc(post.topic)}</p>
        ${post.caption ? `<p class="caption">${esc(post.caption)}</p><button type="button" class="more">Ver legenda completa</button>` : ""}
        ${tags ? `<div class="tags">${esc(tags)}</div>` : ""}
        ${post.error ? `<div class="error">Erro: ${esc(post.error)}</div>` : ""}
        ${canAct && buttons.length ? `<div class="actions">${buttons.join("")}</div>` : ""}
      </div>
    </article>`;
}

function render() {
  renderSummary();
  renderTabs();
  const q = queue();
  let list =
    currentTab === "all" ? [...posts] : posts.filter((p) => effectiveStatus(p).status === currentTab);
  if (currentTab === "accepted") list = q;
  else list.sort((a, b) => b.cycle - a.cycle || a.order - b.order);

  $("#grid").innerHTML = list
    .map((p) => cardHtml(p, currentTab === "accepted" ? q.indexOf(p) + 1 : 0))
    .join("");
  const empty = $("#empty");
  empty.hidden = list.length > 0;
  empty.textContent = posts.length
    ? "Nenhum post nesta categoria."
    : "Ainda não há posts. Eles aparecem aqui após a primeira geração.";
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

let toastTimer;
function toast(msg, isError = false) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.toggle("error", isError);
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 5000);
}

function openSettings() {
  const { repo, token } = settings();
  $("#repo-input").value = repo;
  $("#token-input").value = token;
  $("#settings").showModal();
}

// ---------- eventos ----------
$("#tabs").addEventListener("click", (e) => {
  const tab = e.target.closest("[data-tab]");
  if (!tab) return;
  currentTab = tab.dataset.tab;
  render();
});

$("#grid").addEventListener("click", (e) => {
  const card = e.target.closest(".card");
  if (!card) return;
  if (e.target.classList.contains("more")) {
    const cap = card.querySelector(".caption");
    cap.classList.toggle("open");
    e.target.textContent = cap.classList.contains("open") ? "Recolher legenda" : "Ver legenda completa";
    return;
  }
  const btn = e.target.closest("[data-status]");
  if (!btn) return;
  const post = posts.find((p) => p.id === card.dataset.id);
  setStatus(post, btn.dataset.status, [...card.querySelectorAll(".actions button")]);
});

$("#settings-btn").addEventListener("click", openSettings);
$("#settings").addEventListener("close", () => {
  if ($("#settings").returnValue !== "save") return;
  lsSet("storobot.repo", $("#repo-input").value.trim());
  lsSet("storobot.token", $("#token-input").value.trim());
  toast("Configuração salva neste navegador.");
});

setupPwa();
load();
