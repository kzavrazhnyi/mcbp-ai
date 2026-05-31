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

// ── health ───────────────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const r = await fetch(`${API}/health`);
    const j = await r.json();
    const d = j.data || {};
    const up = d.upstream || {};
    const onec = d.mock_1c ? "mock" : (up.status === "ok" ? "1С ✓" : "1С ✗");
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
    body: JSON.stringify({ message, stream: true }),
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

checkHealth();
setInterval(checkHealth, 30000);
input.focus();
