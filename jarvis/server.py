"""FastAPI app: the router, the tools and the static UI in one process."""

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from jarvis import tools
from jarvis.routers.joint import JointRouter

WEB = Path(__file__).resolve().parent / "web"
state: dict = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    state["router"] = JointRouter()
    yield


app = FastAPI(title="Jarvis", version="2.0.0", lifespan=lifespan)
# Reject foreign Host headers so a web page cannot reach the local API through DNS rebinding.
# A hosted deployment lists its public hostname in JARVIS_ALLOWED_HOSTS (comma separated).
_hosts = ["localhost", "127.0.0.1", "[::1]", "testserver"]
_hosts += [h.strip() for h in os.getenv("JARVIS_ALLOWED_HOSTS", "").split(",") if h.strip()]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_hosts)


@app.middleware("http")
async def revalidate(request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("Cache-Control", "no-cache")  # always revalidate, so a new build is picked up
    return resp


class ChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    tz_offset_min: int = 0
    default_city: str = ""
    history: list[dict] = Field(default=[], max_length=20)


def route_json(r) -> dict:
    return {"tool": r.tool, "confidence": round(r.confidence, 3), "intent": r.intent, "path": r.path,
            "args": r.args, "spans": r.spans, "ms": round(r.ms, 2)}


def run_router(text: str):
    t0 = time.perf_counter()
    r = state["router"].route(text)
    r.ms = (time.perf_counter() - t0) * 1000
    return r


@app.get("/api/health")
def health():
    return {"status": "ok", "router": "joint-int8", "threshold": state["router"].threshold}


@app.post("/api/route")
def route(body: ChatIn):
    """Router only, no side effects. Used by the evidence panel and for debugging."""
    return route_json(run_router(body.text))


@app.post("/api/chat")
async def chat(body: ChatIn):
    r = run_router(body.text)
    action = None
    if r.tool == "WEATHER":
        reply, action = await tools.weather(r.args.get("city") or body.default_city)
    elif r.tool == "SET_REMINDER":
        when = r.args.get("when", "")
        title = r.args.get("title", "")
        derived = tools.reminder_title(body.text, when)
        if derived and (not title or title in derived):  # the tagger often stops a word early ("call" for "call mum")
            title = derived
        reply, action = tools.reminder(when, title, body.tz_offset_min)
    elif r.tool == "SAVE_NOTE":
        reply, action = tools.note(body.text)
    elif r.tool == "GENERAL_QA":
        reply = await tools.answer(body.text, body.history)
    else:
        reply = tools.unsupported(r.intent)
    return {"reply": reply, "action": action, "route": route_json(r)}


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="web")
