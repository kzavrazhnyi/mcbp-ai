"use strict";

// API base: фронтенд віддається тим самим FastAPI, тож шлях відносний.
const API = "/ai/v1";

const chat = document.getElementById("chat");
const emptyState = document.getElementById("empty-state");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const healthDot = document.getElementById("health-dot");
const healthMeta = document.getElementById("health-meta");

let busy = false;
let conversationId = null;

// ── health ───────────────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const r = await fetch(`${API}/health`);
    const j = await r.json();
    const d = j.data || {};
    const up = d.upstream || {};
    const onec = d.mock_1c ? "mock" : (up.status === "ok" ? "BAS ✓" : "BAS ✗");
    healthDot.classList.toggle("ok", r.ok);
    healthDot.classList.toggle("err", !r.ok);
    healthMeta.textContent = `LLM: ${d.llm_provider} · ${onec}`;
  } catch (e) {
    healthDot.classList.add("err");
    healthMeta.textContent = "backend недоступний";
  }
}

// ── DOM helpers ────────────────────────────────────────────────────────────
function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

function errBanner(msg) {
  const d = document.createElement("div");
  d.className = "err-banner";
  d.textContent = msg;
  return d;
}

function addMessage(role, text) {
  if (emptyState) emptyState.remove();
  const wrap = el("div", `msg ${role}`);
  const bubble = el("div", "bubble", text || "");
  wrap.appendChild(bubble);
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
  return bubble;
}

function toolLabel(ev) {
  // короткий опис аргументів інструмента
  const a = ev.arguments || {};
  const parts = [];
  if (a.type) parts.push(a.type);
  if (a.q) parts.push(`q="${a.q}"`);
  if (a.from || a.to) parts.push(`${a.from || "…"}…${a.to || "…"}`);
  if (a.counterparty) parts.push(`cp=${a.counterparty}`);
  return parts.join(" ");
}

function addToolCall(trace, ev) {
  const row = el("div", "tool running");
  row.dataset.name = ev.name;
  const sp = el("span", "spinner");
  const name = el("span", null, ev.name);
  const args = el("code", null, toolLabel(ev));
  row.append(sp, name, args);
  trace.appendChild(row);
  chat.scrollTop = chat.scrollHeight;
  return row;
}

function markToolResult(trace, ev) {
  // знаходимо останній running-рядок цього інструмента
  const rows = [...trace.querySelectorAll(`.tool.running[data-name="${ev.name}"]`)];
  const row = rows[rows.length - 1];
  if (!row) return;
  row.classList.remove("running");
  row.classList.add(ev.ok ? "done" : "fail");
  const sp = row.querySelector(".spinner");
  if (sp) sp.replaceWith(el("span", "ic", ev.ok ? "✓" : "✗"));
  if (!ev.ok && ev.error) {
    row.appendChild(el("code", null, ev.error.slice(0, 80)));
  }
}

// ── SSE через fetch + ReadableStream (POST не підтримує EventSource) ────────
async function streamQuery(message) {
  const assistantWrap = el("div", "msg assistant");
  const trace = el("div", "trace");
  const bubble = el("div", "bubble cursor");
  assistantWrap.append(trace, bubble);
  chat.appendChild(assistantWrap);
  chat.scrollTop = chat.scrollHeight;

  let answered = false;

  const resp = await fetch(`${API}/ai/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, stream: true, conversation_id: conversationId }),
  });

  if (!resp.ok || !resp.body) {
    bubble.classList.remove("cursor");
    bubble.textContent = `Помилка ${resp.status}`;
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buf = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });

    // SSE-кадри розділені порожнім рядком
    const frames = buf.split("\n\n");
    buf = frames.pop(); // останній — можливо неповний

    for (const frame of frames) {
      const line = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      let ev;
      try {
        ev = JSON.parse(line.slice(5).trim());
      } catch {
        continue;
      }
      if (ev.type === "session") { conversationId = ev.conversation_id; continue; }
      handleEvent(ev, { trace, bubble });
      if (ev.type === "answer") answered = true;
    }
  }

  bubble.classList.remove("cursor");
  if (!answered && !bubble.textContent) bubble.textContent = "(порожня відповідь)";
}

function handleEvent(ev, ctx) {
  switch (ev.type) {
    case "tool_call":
      addToolCall(ctx.trace, ev);
      break;
    case "tool_result":
      markToolResult(ctx.trace, ev);
      break;
    case "token": // на майбутнє: токен-стрімінг
      ctx.bubble.textContent += ev.text || "";
      chat.scrollTop = chat.scrollHeight;
      break;
    case "answer":
      ctx.bubble.classList.remove("cursor");
      ctx.bubble.textContent = ev.text || "";
      chat.scrollTop = chat.scrollHeight;
      break;
    case "error":
      ctx.bubble.classList.remove("cursor");
      ctx.bubble.classList.add("err-banner");
      ctx.bubble.textContent = ev.message || "помилка";
      break;
  }
}

// ── send flow ──────────────────────────────────────────────────────────────
async function send(message) {
  if (busy || !message.trim()) return;
  busy = true;
  sendBtn.disabled = true;
  addMessage("user", message);
  input.value = "";
  autoresize();
  try {
    await streamQuery(message.trim());
  } catch (e) {
    addMessage("assistant", "Помилка з'єднання: " + e.message);
  } finally {
    busy = false;
    sendBtn.disabled = false;
    input.focus();
  }
}

// ── UI wiring ──────────────────────────────────────────────────────────────
function autoresize() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 180) + "px";
}

input.addEventListener("input", autoresize);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    send(input.value);
  }
});
form.addEventListener("submit", (e) => {
  e.preventDefault();
  send(input.value);
});
document.querySelectorAll(".chip").forEach((b) =>
  b.addEventListener("click", () => send(b.dataset.q))
);

document.getElementById("new-chat-btn").addEventListener("click", () => {
  conversationId = null;
  chat.innerHTML = "";
  const empty = document.createElement("div");
  empty.id = "empty-state";
  empty.className = "empty";
  empty.innerHTML = '<h1>Запитайте про дані <a href="https://www.bas-soft.eu/" target="_blank" rel="noopener">BAS</a></h1>' +
    "<p>Модель сама вирішує, які дані тягнути через інструменти MCBP_AI.</p>";
  chat.appendChild(empty);
  input.focus();
});

checkHealth();
setInterval(checkHealth, 30000);
input.focus();

// ── Data Browser ──────────────────────────────────────────────────────────────

const dataBrowser   = document.getElementById("data-browser");
const dbKindSel     = document.getElementById("db-kind");
const dbSearchWrap  = document.getElementById("db-search-wrap");
const dbDateWrap    = document.getElementById("db-date-wrap");
const dbSearchInp   = document.getElementById("db-search");
const dbFromInp     = document.getElementById("db-from");
const dbToInp       = document.getElementById("db-to");
const dbLoadBtn     = document.getElementById("db-load-btn");
const dbTypesRow    = document.getElementById("db-types-row");
const dbContent     = document.getElementById("db-content");
const dbDetail      = document.getElementById("db-detail");
const dbDetailTitle = document.getElementById("db-detail-title");
const dbDetailBody  = document.getElementById("db-detail-body");

let dbKind = "";
let dbSelectedType = "";

// Tab switching
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b === btn));
    const isChat = tab === "chat";
    chat.classList.toggle("hidden", !isChat);
    form.classList.toggle("hidden", !isChat);
    dataBrowser.classList.toggle("hidden", isChat);
  });
});

// Kind selector
dbKindSel.addEventListener("change", async () => {
  dbKind = dbKindSel.value;
  dbSelectedType = "";
  dbLoadBtn.disabled = true;
  dbTypesRow.innerHTML = "";
  dbTypesRow.classList.add("hidden");
  dbContent.innerHTML = "";
  dbDetail.classList.add("hidden");
  dbSearchWrap.classList.toggle("hidden", dbKind !== "Catalogs");
  dbDateWrap.classList.toggle("hidden", dbKind !== "Documents");
  if (!dbKind) return;

  dbTypesRow.innerHTML = '<span class="db-spinner"><span class="spinner"></span></span>';
  dbTypesRow.classList.remove("hidden");
  try {
    const r = await fetch(`${API}/metadata/${encodeURIComponent(dbKind)}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const j = await r.json();
    const items = j.items || [];
    dbTypesRow.innerHTML = "";
    if (!items.length) {
      dbTypesRow.innerHTML = '<span style="color:var(--muted);font-size:.85rem">Немає елементів</span>';
      return;
    }
    items.forEach((item) => {
      const btn = document.createElement("button");
      btn.className = "chip";
      btn.textContent = item.synonym || item.name;
      btn.title = item.name;
      btn.addEventListener("click", () => {
        dbTypesRow.querySelectorAll(".chip").forEach((b) => b.classList.toggle("active", b === btn));
        dbSelectedType = item.name;
        dbLoadBtn.disabled = false;
      });
      dbTypesRow.appendChild(btn);
    });
  } catch (e) {
    dbTypesRow.innerHTML = "";
    dbTypesRow.appendChild(errBanner("Помилка: " + e.message));
  }
});

// Load data button
dbLoadBtn.addEventListener("click", async () => {
  if (!dbSelectedType) return;
  dbContent.innerHTML = '<div class="db-spinner"><span class="spinner"></span> Завантаження…</div>';
  dbDetail.classList.add("hidden");
  const params = new URLSearchParams();
  let url;
  if (dbKind === "Catalogs") {
    url = `${API}/catalogs/${encodeURIComponent(dbSelectedType)}`;
    const q = dbSearchInp.value.trim();
    if (q) params.set("q", q);
  } else if (dbKind === "Documents") {
    url = `${API}/documents/${encodeURIComponent(dbSelectedType)}`;
    if (dbFromInp.value) params.set("from", dbFromInp.value);
    if (dbToInp.value) params.set("to", dbToInp.value);
  } else {
    url = `${API}/metadata/${encodeURIComponent(dbKind)}/${encodeURIComponent(dbSelectedType)}`;
  }
  try {
    const qs = params.toString();
    const r = await fetch(url + (qs ? "?" + qs : ""));
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      dbContent.innerHTML = "";
      dbContent.appendChild(errBanner(err.detail || r.statusText));
      return;
    }
    const j = await r.json();
    if (dbKind === "Catalogs" || dbKind === "Documents") {
      renderDbTable(j.data || [], dbKind, dbSelectedType);
    } else {
      renderDbMeta(j);
    }
  } catch (e) {
    dbContent.innerHTML = "";
    dbContent.appendChild(errBanner("Помилка: " + e.message));
  }
});

function renderDbTable(rows, kind, type_) {
  if (!rows.length) {
    dbContent.innerHTML = '<div class="db-empty">Записів не знайдено</div>';
    return;
  }
  const first = rows[0];
  const cols = Object.keys(first).filter((k) => k !== "Ref" && typeof first[k] !== "object");
  const tbl = document.createElement("table");
  tbl.className = "db-table";
  const thead = tbl.createTHead();
  const hr = thead.insertRow();
  cols.forEach((c) => {
    const th = document.createElement("th");
    th.textContent = c;
    hr.appendChild(th);
  });
  const tbody = tbl.createTBody();
  rows.forEach((row) => {
    const tr = tbody.insertRow();
    tr.className = "db-row";
    cols.forEach((c) => {
      const td = tr.insertCell();
      const v = row[c];
      td.textContent = v === null || v === undefined ? "" : String(v);
    });
    if (row.Ref && row.Ref.Data) {
      tr.addEventListener("click", () => openDbDetail(row, kind, type_));
    }
  });
  dbContent.innerHTML = "";
  dbContent.appendChild(tbl);
}

function renderDbMeta(j) {
  const attrs = [...(j.standard_attributes || []), ...(j.attributes || [])];
  if (!attrs.length) {
    dbContent.innerHTML = '<div class="db-empty">Реквізити відсутні</div>';
    return;
  }
  const tbl = document.createElement("table");
  tbl.className = "db-table";
  const thead = tbl.createTHead();
  const hr = thead.insertRow();
  ["Ім'я", "Синонім", "Тип"].forEach((h) => {
    const th = document.createElement("th");
    th.textContent = h;
    hr.appendChild(th);
  });
  const tbody = tbl.createTBody();
  attrs.forEach((a) => {
    const tr = tbody.insertRow();
    [a.name || "", a.synonym || "", (a.types || []).join(", ")].forEach((v) => {
      const td = tr.insertCell();
      td.textContent = v;
    });
  });
  dbContent.innerHTML = "";
  dbContent.appendChild(tbl);
}

async function openDbDetail(row, kind, type_) {
  dbDetail.classList.remove("hidden");
  dbDetailTitle.textContent = (row.Ref && row.Ref.Presentation) || type_;
  dbDetailBody.innerHTML = '<div class="db-spinner"><span class="spinner"></span></div>';
  try {
    const r = await fetch(
      `${API}/object/${encodeURIComponent(kind)}/${encodeURIComponent(type_)}/${encodeURIComponent(row.Ref.Data)}`
    );
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      dbDetailBody.innerHTML = "";
      dbDetailBody.appendChild(errBanner(err.detail || r.statusText));
      return;
    }
    const j = await r.json();
    renderDbDetailBody(j.data ?? j);
  } catch (e) {
    dbDetailBody.innerHTML = "";
    dbDetailBody.appendChild(errBanner("Помилка: " + e.message));
  }
}

function renderDbDetailBody(data) {
  const tbl = document.createElement("table");
  tbl.className = "db-table";
  const entries = Array.isArray(data)
    ? data.flatMap((o) => Object.entries(o))
    : Object.entries(data);
  entries.forEach(([k, v]) => {
    const tr = tbl.insertRow();
    const tk = tr.insertCell();
    tk.className = "db-detail-key";
    tk.textContent = k;
    const tv = tr.insertCell();
    tv.textContent = typeof v === "object" ? JSON.stringify(v) : String(v ?? "");
  });
  dbDetailBody.innerHTML = "";
  dbDetailBody.appendChild(tbl);
}

document.getElementById("db-detail-close").addEventListener("click", () => {
  dbDetail.classList.add("hidden");
});
