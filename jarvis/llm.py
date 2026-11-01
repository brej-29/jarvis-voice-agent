"""Optional language model for general questions, through any OpenAI-compatible endpoint.

Settings come from the environment or a `.env` file (never committed, never sent to the browser):
    LLM_ENDPOINT         chat completions URL (or a base URL ending in /v1)
    LLM_API_KEY          bearer token, if the endpoint needs one
    LLM_MODEL            model or combo id (falls back to DEFAULT_MODEL when unset or a placeholder)
    LLM_PRICE_IN_PER_M   USD per million input tokens (optional, 0 for free models)
    LLM_PRICE_OUT_PER_M  USD per million output tokens (optional)
    MONTHLY_BUDGET_USD   stop calling the model once this much has been spent (optional)
    LLM_MAX_CALLS_PER_DAY   hard cap on calls per day, default 300
The older JARVIS_LLM_BASE_URL / JARVIS_LLM_MODEL / JARVIS_LLM_API_KEY names still work.
"""

import json
import os
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path

import httpx

DEFAULT_MODEL = "auto/best-free"  # a free OmniRoute combo, see D:/Project/models.md
SYSTEM = ("You are Jarvis, a voice assistant. Answer in one or two short spoken sentences. "
          "No markdown, no lists, no emoji.")
SPEND_FILE = Path(os.getenv("JARVIS_SPEND_FILE", ".jarvis_spend.json"))


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env reader: KEY=VALUE lines, existing environment variables win."""
    for p in [path] if path else [Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env"]:
        if p and p.is_file():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _num(name: str) -> float:
    try:
        return max(0.0, float(os.getenv(name, "")))
    except ValueError:  # unset or a "<placeholder>"
        return 0.0


def settings() -> dict:
    endpoint = os.getenv("LLM_ENDPOINT") or os.getenv("JARVIS_LLM_BASE_URL") or ""
    if endpoint and not endpoint.rstrip("/").endswith("/chat/completions"):
        endpoint = endpoint.rstrip("/") + "/chat/completions"
    model = os.getenv("LLM_MODEL") or os.getenv("JARVIS_LLM_MODEL") or ""
    if not model or model.startswith("<"):
        model = DEFAULT_MODEL
    key = os.getenv("LLM_API_KEY") or os.getenv("JARVIS_LLM_API_KEY") or ""
    return {"endpoint": endpoint if not endpoint.startswith("<") else "", "model": model,
            "key": "" if key.startswith("<") else key, "price_in": _num("LLM_PRICE_IN_PER_M"),
            "price_out": _num("LLM_PRICE_OUT_PER_M"), "budget": _num("MONTHLY_BUDGET_USD"),
            "max_calls": int(_num("LLM_MAX_CALLS_PER_DAY") or 300)}


def _ledger() -> dict:
    try:
        d = json.loads(SPEND_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    month, today = date.today().strftime("%Y-%m"), date.today().isoformat()
    if d.get("month") != month:
        d["month"], d["usd"] = month, 0.0
    if d.get("day") != today:
        d["day"], d["calls"] = today, 0
    return d


def status() -> dict:
    s, d = settings(), _ledger()
    return {"connected": bool(s["endpoint"]), "model": s["model"], "spent_usd": round(d.get("usd", 0.0), 4),
            "budget_usd": s["budget"] or None, "calls_today": d.get("calls", 0)}


def _blocked(s: dict, d: dict) -> str:
    if s["budget"] and d.get("usd", 0.0) >= s["budget"]:
        return "My language model budget for this month is used up, so I cannot answer general questions until it resets."
    if d.get("calls", 0) >= s["max_calls"]:
        return "I have reached today's limit of language model calls. Try again tomorrow."
    return ""


def _record(s: dict, tokens_in: int, tokens_out: int) -> None:
    d = _ledger()
    d["calls"] = d.get("calls", 0) + 1
    d["usd"] = d.get("usd", 0.0) + (tokens_in * s["price_in"] + tokens_out * s["price_out"]) / 1e6
    try:
        SPEND_FILE.write_text(json.dumps(d), encoding="utf-8")
    except OSError:
        pass


def _messages(text: str, history: list[dict] | None) -> list[dict]:
    # the browser supplies the history, so keep only plain user/assistant turns of bounded size
    past = [{"role": h["role"], "content": str(h.get("content", ""))[:500]} for h in (history or [])[-6:]
            if isinstance(h, dict) and h.get("role") in ("user", "assistant")]
    return [{"role": "system", "content": SYSTEM}, *past, {"role": "user", "content": text}]


NOT_CONNECTED = ("General questions need a language model and none is connected. Set LLM_ENDPOINT and "
                 "LLM_API_KEY in a .env file. Weather, reminders and notes work without one.")
FAILED = "My language model did not answer. Try again in a moment."


async def stream_answer(text: str, history: list[dict] | None = None,
                        client: httpx.AsyncClient | None = None) -> AsyncIterator[str]:
    """Yield the reply in pieces. Never raises: failures become a spoken message."""
    s, d = settings(), _ledger()
    if not s["endpoint"]:
        yield NOT_CONNECTED
        return
    if msg := _blocked(s, d):
        yield msg
        return
    body = {"model": s["model"], "messages": _messages(text, history), "max_tokens": 200,
            "temperature": 0.3, "stream": True, "stream_options": {"include_usage": True}}
    headers = {"Authorization": f"Bearer {s['key']}"} if s["key"] else {}
    out_chars, usage = 0, None
    try:
        async with (client or httpx.AsyncClient(timeout=httpx.Timeout(45, connect=5))) as c, \
                c.stream("POST", s["endpoint"], headers=headers, json=body) as r:
            if r.status_code != 200:
                yield FAILED
                return
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                chunk = json.loads(payload)
                usage = chunk.get("usage") or usage
                for ch in chunk.get("choices") or []:
                    piece = ((ch.get("delta") or {}).get("content") or "").replace(chr(0x202f), " ")
                    if piece:
                        out_chars += len(piece)
                        yield piece
    except (httpx.HTTPError, ValueError, KeyError):
        yield FAILED
        return
    prompt_chars = sum(len(m["content"]) for m in body["messages"])
    _record(s, (usage or {}).get("prompt_tokens") or prompt_chars // 4,
            (usage or {}).get("completion_tokens") or out_chars // 4)


async def answer(text: str, history: list[dict] | None = None) -> str:
    return "".join([p async for p in stream_answer(text, history)]).strip()
