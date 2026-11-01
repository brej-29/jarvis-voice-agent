from fastapi.testclient import TestClient

from jarvis.server import app


def test_routes_and_declines():
    with TestClient(app) as c:
        assert c.get("/api/health").json()["status"] == "ok"
        r = c.post("/api/chat", json={"text": "play some jazz in the kitchen"}).json()
        assert r["route"]["tool"] == "UNSUPPORTED" and r["action"] is None
        r = c.post("/api/chat", json={"text": "save a note buy oat milk"}).json()
        assert r["route"]["tool"] == "SAVE_NOTE" and r["action"]["type"] == "note"
        r = c.post("/api/chat", json={"text": "remind me to call mum tomorrow at 5 pm", "tz_offset_min": 0}).json()
        assert r["route"]["tool"] == "SET_REMINDER" and r["action"]["type"] == "reminder"


def test_foreign_host_rejected():
    with TestClient(app, base_url="http://evil.example") as c:
        assert c.get("/api/health").status_code == 400
