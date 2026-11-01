import { renderEvidence } from "./evidence.js";

const $ = (s) => document.querySelector(s);
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } },
};
const TOOL_LABEL = { WEATHER: "Weather", SET_REMINDER: "Reminder", SAVE_NOTE: "Note", GENERAL_QA: "Answer", UNSUPPORTED: "Not done" };
let threshold = 0.85;
const history = [];

/* ---------- tabs ---------- */
function showTab() {
  const tab = location.hash === "#evidence" ? "evidence" : "talk";
  for (const v of document.querySelectorAll(".view")) v.hidden = v.id !== tab;
  for (const a of document.querySelectorAll("[data-tab]")) a.toggleAttribute("aria-current", a.dataset.tab === tab) || a.removeAttribute("aria-current");
  for (const a of document.querySelectorAll("[data-tab]")) if (a.dataset.tab === tab) a.setAttribute("aria-current", "page");
  if (tab === "evidence" && !$("#ev-root").dataset.ready) { $("#ev-root").dataset.ready = "1"; renderEvidence($("#ev-root")); }
  window.scrollTo(0, 0);
}
addEventListener("hashchange", showTab);
showTab();

/* ---------- health ---------- */
async function health() {
  const s = $("#status");
  try {
    const h = await (await fetch("api/health")).json();
    threshold = h.threshold;
    s.textContent = "Router ready, running on this machine";
    s.className = "status ok";
  } catch {
    s.textContent = "Router offline. Waking up can take up to a minute on the free host.";
    s.className = "status bad";
    setTimeout(health, 4000);
  }
}
health();

/* ---------- feed ---------- */
function esc(t) { return t.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

function markSpans(text, spans) {
  let html = esc(text);
  for (const sp of spans || []) {
    const re = new RegExp("\\b" + sp.text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b", "i");
    html = html.replace(re, (m) => `<mark class="s-${sp.kind}">${m}</mark>`);
  }
  return html;
}

function addSlip(text, data, pending) {
  $("#empty").hidden = true;
  $("#clear").hidden = false;
  const li = document.createElement("li");
  li.className = "slip";
  if (pending) {
    li.innerHTML = `<p class="said">${esc(text)}</p><p class="reply thinking">Routing</p>`;
    $("#feed").prepend(li);
    return li;
  }
  fill(li, text, data);
  return li;
}

function fill(li, text, d) {
  const r = d.route, no = r.tool === "UNSUPPORTED";
  li.classList.toggle("is-no", no);
  li.classList.add("enter");
  const slots = Object.entries(r.args || {}).filter(([, v]) => v).map(([k, v]) => `${k}: ${esc(String(v))}`).join(", ");
  const how = r.path === "abstain" ? "Unsure, so it declined" : r.path === "llm" ? "Asked the language model" : "Fast path";
  li.innerHTML = `
    <p class="said">${markSpans(text, r.spans)}</p>
    <div class="verdict">
      <span class="chip t-${r.tool.toLowerCase()}">${TOOL_LABEL[r.tool]}</span>
      <span class="meter" style="--v:${r.confidence};--th:${threshold}" role="img" aria-label="Router confidence ${Math.round(r.confidence * 100)} percent, decline threshold ${Math.round(threshold * 100)} percent"></span>
      <span class="meta">${Math.round(r.confidence * 100)}% sure, ${r.ms.toFixed(1)} ms${slots ? ", " + slots : ""}</span>
    </div>
    <p class="reply">${esc(d.reply)}</p>
    <p class="meta">${how}${r.intent ? ", heard as " + r.intent.replace(/_/g, " ") : ""}</p>`;
}

/* ---------- actions on this device ---------- */
const timers = new Map();
function schedule(rem) {
  const ms = new Date(rem.at) - Date.now();
  if (ms <= 0 || ms > 2 ** 31 - 1) return;
  timers.set(rem.at + rem.title, setTimeout(() => {
    if ("Notification" in window && Notification.permission === "granted") new Notification("Jarvis reminder", { body: rem.title });
    flash(`Reminder: ${rem.title}`);
    speak(`Reminder: ${rem.title}`);
  }, ms));
}
function flash(msg) { $("#status").textContent = msg; setTimeout(health, 6000); }
function renderSaved() {
  const rems = store.get("reminders", []).filter((r) => new Date(r.at) > Date.now());
  const notes = store.get("notes", []);
  $("#saved").innerHTML = [...rems.map((r) => `<div class="item">${esc(r.title)}<small>${new Date(r.at).toLocaleString()}</small></div>`),
    ...notes.map((n) => `<div class="item">${esc(n.text)}<small>note</small></div>`)].join("") || "<p>Nothing saved on this device yet.</p>";
}
function perform(action) {
  if (!action) return;
  if (action.type === "reminder") {
    store.set("reminders", [...store.get("reminders", []), action]);
    schedule(action);
    if ("Notification" in window && Notification.permission === "default") Notification.requestPermission();
  } else if (action.type === "note") {
    store.set("notes", [{ text: action.text, at: new Date().toISOString() }, ...store.get("notes", [])]);
  }
  renderSaved();
}
store.get("reminders", []).forEach(schedule);
renderSaved();

/* ---------- speech out ---------- */
function speak(t) {
  if (!$("#speak").checked || !("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  speechSynthesis.speak(new SpeechSynthesisUtterance(t));
}
$("#speak").checked = store.get("speak", false);
$("#speak").addEventListener("change", (e) => store.set("speak", e.target.checked));
$("#city").value = store.get("city", "");
$("#city").addEventListener("change", (e) => store.set("city", e.target.value.trim()));

/* ---------- send ---------- */
async function send(text) {
  text = text.trim();
  if (!text) return;
  $("#text").value = "";
  const li = addSlip(text, null, true);
  try {
    const res = await fetch("api/chat", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, tz_offset_min: -new Date().getTimezoneOffset(), default_city: $("#city").value.trim(), history }) });
    if (!res.ok) throw new Error(res.status);
    const d = await res.json();
    fill(li, text, d);
    perform(d.action);
    history.push({ role: "user", content: text }, { role: "assistant", content: d.reply });
    speak(d.reply);
  } catch {
    li.innerHTML = `<p class="said">${esc(text)}</p><p class="reply">The router did not answer. If this is the free hosted copy, it may be waking up: wait a few seconds and send again.</p>`;
  }
}
$("#form").addEventListener("submit", (e) => { e.preventDefault(); send($("#text").value); });
for (const b of document.querySelectorAll("[data-say]")) b.addEventListener("click", () => send(b.dataset.say));
$("#clear").addEventListener("click", () => { $("#feed").innerHTML = ""; $("#empty").hidden = false; $("#clear").hidden = true; });

/* ---------- voice in ---------- */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const mic = $("#mic");
if (!SR) {
  mic.disabled = true;
  $("#voice-hint").textContent = "Voice input needs Chrome or Edge. Typing works in any browser.";
} else {
  let rec = null, raf = 0, stream = null, ctx = null;
  const cv = $("#level"), g = cv.getContext("2d");
  const draw = (an, buf) => {
    an.getByteTimeDomainData(buf);
    let s = 0; for (const v of buf) s += Math.abs(v - 128); const lvl = Math.min(1, (s / buf.length) / 30);
    g.clearRect(0, 0, 120, 120);
    g.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue("--reminder");
    g.lineWidth = 3; g.beginPath(); g.arc(60, 60, 36 + lvl * 20, 0, 7); g.stroke();
    raf = requestAnimationFrame(() => draw(an, buf));
  };
  const stop = () => { mic.setAttribute("aria-pressed", "false"); cancelAnimationFrame(raf); stream?.getTracks().forEach((t) => t.stop()); ctx?.close(); stream = ctx = null; };
  mic.addEventListener("click", async () => {
    if (rec) { rec.stop(); return; }
    rec = new SR(); rec.lang = navigator.language || "en-US"; rec.interimResults = true; rec.maxAlternatives = 1;
    let last = "";
    rec.onresult = (e) => { last = [...e.results].map((r) => r[0].transcript).join(" "); $("#text").value = last; };
    rec.onerror = (e) => { $("#voice-hint").textContent = e.error === "not-allowed" ? "Microphone access is blocked. Allow it in the address bar, or type instead." : "Could not hear that. Try again or type."; };
    rec.onend = () => { rec = null; stop(); if (last) send(last); };
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      ctx = new AudioContext(); const an = ctx.createAnalyser(); an.fftSize = 512;
      ctx.createMediaStreamSource(stream).connect(an); draw(an, new Uint8Array(an.fftSize));
    } catch { /* level ring is optional */ }
    $("#voice-hint").textContent = "Listening. Click the microphone again when you are done.";
    mic.setAttribute("aria-pressed", "true");
    rec.start();
  });
  $("#voice-hint").textContent = "Click the microphone and speak, or type below. Speech recognition runs in your browser.";
}

/* ?say=text prefills the input only. Nothing runs until the person presses Send, so a shared link
   cannot save notes, set reminders or spend LLM calls on its own. */
const preset = new URLSearchParams(location.search).get("say");
if (preset) $("#text").value = preset.slice(0, 300);
