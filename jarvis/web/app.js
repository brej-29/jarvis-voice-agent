import { chat, health as engineHealth, STATIC } from "./engine.js";
import { renderEvidence } from "./evidence.js";
import { createOrb } from "./orb.js";

document.documentElement.classList.add("js");
const $ = (s) => document.querySelector(s);
const reduced = matchMedia("(prefers-reduced-motion: reduce)");
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } },
};
const TOOL_LABEL = { WEATHER: "Weather", SET_REMINDER: "Reminder", SAVE_NOTE: "Note", GENERAL_QA: "Answer", UNSUPPORTED: "Not done" };
const ACTED = { WEATHER: "Looked up", SET_REMINDER: "Reminder set", SAVE_NOTE: "Note saved", GENERAL_QA: "Asked the model" };
let threshold = 0.85, llm = { connected: false };
const history = [];
const orb = createOrb($("#orb"));

/* ---------- state: one value drives the orb, the aurora and the caption ---------- */
let state = "idle", settleTimer = 0;
function setState(s, then = 0) {
  clearTimeout(settleTimer);
  state = s;
  document.body.dataset.state = s;
  orb.setState(s);
  if (then) settleTimer = setTimeout(() => setState("idle"), then);
}
const caption = (t) => { $("#caption").textContent = t; };
const IDLE_CAPTION = "Ask for something. Jarvis decides whether to do it.";

/* ---------- tabs ---------- */
function showTab() {
  const tab = location.hash === "#evidence" ? "evidence" : "talk";
  for (const v of document.querySelectorAll(".view")) v.hidden = v.id !== tab;
  for (const a of document.querySelectorAll("[data-tab]")) {
    if (a.dataset.tab === tab) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  }
  if (tab === "evidence" && !$("#ev-root").dataset.ready) { $("#ev-root").dataset.ready = "1"; renderEvidence($("#ev-root")); }
  window.scrollTo(0, 0);
}
addEventListener("hashchange", showTab);
showTab();

/* ---------- health ---------- */
async function health() {
  const s = $("#status");
  try {
    const h = await engineHealth();
    threshold = h.threshold;
    llm = h.llm || llm;
    const where = STATIC ? "Router ready, running in your browser" : "Router ready, running on this machine";
    s.textContent = `${where}. ${llm.connected ? "Answers from " + llm.model : "No language model connected"}`;
    s.className = "status ok";
  } catch {
    s.textContent = STATIC ? "Loading the 23 MB router into your browser" : "Router offline. Check that the Jarvis app is running.";
    s.className = "status bad";
    setTimeout(health, 4000);
  }
}
health();

/* ---------- slips ---------- */
function esc(t) { return t.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

function markSpans(text, spans) {
  // find each span in the raw text, then escape piece by piece so inserted markup is never searched
  const lower = text.toLowerCase(), hits = [];
  for (const sp of spans || []) {
    const i = lower.indexOf(sp.text.toLowerCase());
    if (i >= 0 && !hits.some((h) => i < h.end && i + sp.text.length > h.start)) hits.push({ start: i, end: i + sp.text.length, kind: sp.kind });
  }
  hits.sort((a, b) => a.start - b.start);
  let out = "", at = 0;
  for (const h of hits) {
    out += esc(text.slice(at, h.start)) + `<mark class="s-${h.kind}">${esc(text.slice(h.start, h.end))}</mark>`;
    at = h.end;
  }
  return out + esc(text.slice(at));
}

function newSlip(text) {
  $("#empty").hidden = true;
  $("#clear").hidden = false;
  const feed = $("#feed");
  const before = [...feed.children].map((el) => [el, el.getBoundingClientRect().top]);
  const li = document.createElement("li");
  li.className = "slip enter";
  li.innerHTML = `<p class="said">${esc(text)}</p>
    <ol class="trace" aria-label="Steps">
      <li class="on"><b></b><span>Heard</span></li><li><b></b><span>Routed</span></li>
      <li><b></b><span>Acted</span></li><li><b></b><span>Replied</span></li></ol>
    <div class="verdict" hidden></div>
    <p class="reply"><span class="shimmer"></span></p>
    <p class="meta fine" hidden></p>`;
  feed.prepend(li);
  if (!reduced.matches) { // FLIP: the older slips glide down instead of jumping
    for (const [el, top] of before) {
      const dy = top - el.getBoundingClientRect().top;
      if (dy) el.animate([{ transform: `translateY(${dy}px)` }, { transform: "none" }], { duration: 420, easing: "cubic-bezier(.2,.8,.2,1)" });
    }
  }
  return li;
}

function showRoute(li, text, r) {
  const no = r.tool === "UNSUPPORTED", name = r.tool.toLowerCase();
  li.dataset.tool = name;
  li.classList.toggle("is-no", no);
  li.querySelector(".said").innerHTML = markSpans(text, r.spans);
  const steps = li.querySelectorAll(".trace li");
  steps[1].classList.add("on");
  steps[1].querySelector("span").innerHTML = `Routed<small>${r.ms < 10 ? r.ms.toFixed(1) : Math.round(r.ms)} ms</small>`;
  if (no) {
    steps[2].classList.add("stop");
    steps[2].querySelector("span").textContent = "Did not act";
    steps[3].remove();
  } else {
    const acted = r.tool !== "GENERAL_QA" ? ACTED[r.tool] : r.intent === "general_greet" ? "Answered" : llm.connected ? ACTED.GENERAL_QA : "No model connected";
    steps[2].querySelector("span").textContent = acted;
  }
  const slots = Object.entries(r.args || {}).filter(([, v]) => v).map(([k, v]) => `${k}: ${esc(String(v))}`).join(", ");
  const how = r.path === "abstain" ? "Unsure, so it declined" : r.path === "llm" ? "Asked the language model" : "Fast path";
  const v = li.querySelector(".verdict");
  v.hidden = false;
  v.innerHTML = `<span class="chip">${TOOL_LABEL[r.tool]}</span>
    <span class="meter" style="--v:${r.confidence};--th:${threshold}" role="img" aria-label="Router confidence ${Math.round(r.confidence * 100)} percent, decline threshold ${Math.round(threshold * 100)} percent"></span>
    <span class="meta">${Math.round(r.confidence * 100)}% sure${slots ? ", " + slots : ""}</span>`;
  const m = li.querySelector(".meta.fine");
  m.hidden = false;
  m.textContent = `${how}${r.intent ? ", heard as " + r.intent.replace(/_/g, " ") : ""}`;
  caption(`${TOOL_LABEL[r.tool]}, ${Math.round(r.confidence * 100)}% sure`);
}

/* ---------- actions on this device ---------- */
const timers = new Map();
function schedule(rem) {
  const ms = new Date(rem.at) - Date.now();
  if (ms <= 0 || ms > 2 ** 31 - 1) return;
  timers.set(rem.at + rem.title, setTimeout(() => {
    if ("Notification" in window && Notification.permission === "granted") new Notification("Jarvis reminder", { body: rem.title });
    caption(`Reminder: ${rem.title}`);
    speak(`Reminder: ${rem.title}`);
  }, ms));
}
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
  const u = new SpeechSynthesisUtterance(t);
  u.onstart = () => setState("speaking");
  u.onend = u.onerror = () => setState("idle");
  speechSynthesis.speak(u);
}
$("#speak").checked = store.get("speak", false);
$("#speak").addEventListener("change", (e) => store.set("speak", e.target.checked));
$("#city").value = store.get("city", "");
$("#city").addEventListener("change", (e) => store.set("city", e.target.value.trim()));

/* ---------- send ---------- */
let busy = false;
async function send(text) {
  text = text.trim();
  if (!text || busy) return;
  busy = true;
  $("#text").value = "";
  $(".send").disabled = true;
  setState("thinking");
  caption("Routing");
  const li = newSlip(text);
  const reply = li.querySelector(".reply");
  let streamed = "";
  try {
    const d = await chat({ text, tz_offset_min: -new Date().getTimezoneOffset(), default_city: $("#city").value.trim(), history }, {
      route: (r) => showRoute(li, text, r),
      token: (piece) => {
        if (!streamed) { reply.textContent = ""; li.querySelectorAll(".trace li")[2]?.classList.add("on"); }
        streamed += piece;
        reply.textContent = streamed;
        const caret = document.createElement("span");
        caret.className = "caret";
        reply.append(caret);
      },
    });
    reply.textContent = d.reply;
    const steps = li.querySelectorAll(".trace li");
    if (d.route.tool !== "UNSUPPORTED") steps.forEach((s) => s.classList.add("on"));
    perform(d.action);
    history.push({ role: "user", content: text }, { role: "assistant", content: d.reply });
    if (d.route.tool === "UNSUPPORTED") setState("declined", 1600);
    else setState("idle");
    caption(d.route.tool === "UNSUPPORTED" ? "Declined. Nothing was done." : IDLE_CAPTION);
    speak(d.reply);
  } catch {
    li.removeAttribute("data-tool");
    reply.textContent = "The router did not answer. In the hosted copy the model may still be loading: wait a few seconds and send again.";
    setState("idle");
    caption(IDLE_CAPTION);
  } finally {
    busy = false;
    $(".send").disabled = false;
  }
}
$("#form").addEventListener("submit", (e) => { e.preventDefault(); send($("#text").value); });
for (const b of document.querySelectorAll("[data-say]")) b.addEventListener("click", () => send(b.dataset.say));
$("#clear").addEventListener("click", () => { $("#feed").innerHTML = ""; $("#empty").hidden = false; $("#clear").hidden = true; });
addEventListener("keydown", (e) => { // "/" jumps to the input, Escape stops listening; neither animates
  if (e.key === "/" && !/input|textarea/i.test(document.activeElement?.tagName)) { e.preventDefault(); $("#text").focus(); }
  if (e.key === "Escape") stopListening?.();
});

/* ---------- voice in ---------- */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const mic = $("#mic");
let stopListening = null;
if (!SR) {
  mic.disabled = true;
  $("#voice-hint").textContent = "Voice input needs Chrome or Edge. Typing works in any browser.";
} else {
  let rec = null, raf = 0, stream = null, ctx = null;
  const level = (an, buf) => {
    an.getByteTimeDomainData(buf);
    let s = 0; for (const v of buf) s += Math.abs(v - 128);
    orb.setLevel(Math.min(1, (s / buf.length) / 24));
    raf = requestAnimationFrame(() => level(an, buf));
  };
  const cleanup = () => {
    mic.setAttribute("aria-pressed", "false");
    cancelAnimationFrame(raf); orb.setLevel(0);
    stream?.getTracks().forEach((t) => t.stop()); ctx?.close(); stream = ctx = null;
  };
  stopListening = () => rec?.stop();
  mic.addEventListener("click", async () => {
    if (rec) { rec.stop(); return; }
    if (busy) return;
    rec = new SR(); rec.lang = navigator.language || "en-US"; rec.interimResults = true; rec.maxAlternatives = 1;
    let last = "";
    rec.onresult = (e) => { last = [...e.results].map((r) => r[0].transcript).join(" "); $("#text").value = last; caption(last); };
    rec.onerror = (e) => { $("#voice-hint").textContent = e.error === "not-allowed" ? "Microphone access is blocked. Allow it in the address bar, or type instead." : "Could not hear that. Try again or type."; };
    rec.onend = () => { rec = null; cleanup(); if (last) send(last); else { setState("idle"); caption(IDLE_CAPTION); } };
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      ctx = new AudioContext(); const an = ctx.createAnalyser(); an.fftSize = 512;
      ctx.createMediaStreamSource(stream).connect(an); level(an, new Uint8Array(an.fftSize));
    } catch { /* the level meter is optional */ }
    $("#voice-hint").textContent = "";
    mic.setAttribute("aria-pressed", "true");
    setState("listening"); caption("Listening");
    rec.start();
  });
  $("#voice-hint").textContent = "Click the orb and speak, or type. Speech recognition runs in your browser. Press / to type.";
}

/* ?say=text prefills the input only. Nothing runs until the person presses Send, so a shared link
   cannot save notes, set reminders or spend LLM calls on its own. */
const preset = new URLSearchParams(location.search).get("say");
if (preset) $("#text").value = preset.slice(0, 300);
