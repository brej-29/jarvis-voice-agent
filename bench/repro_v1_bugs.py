"""Reproduce two defects in Jarvis V1 by executing its original code from the backup tag.

    python bench/repro_v1_bugs.py
Writes bench/results/v1_bugs.json. Needs git and the V1 dependencies (fastapi, httpx, dateparser).
"""

import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

TAG = "backup/pre-rebuild-2026-11-01"
ROOT = Path(__file__).resolve().parents[1]


def extract(dest: Path):
    tar = subprocess.run(["git", "archive", TAG, "backend/app", "context"], cwd=ROOT,
                         capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=tar, check=True)


def main():
    out = {"tag": TAG}
    with tempfile.TemporaryDirectory() as tmp:
        extract(Path(tmp))
        sys.path.insert(0, str(Path(tmp) / "backend"))
        from app.routers import chat  # noqa: E402

        try:
            chat._handle_save_note_tool({"title": "milk", "content": "buy milk"}, [])
            out["save_note"] = "ok"
        except Exception as e:  # the defect: datetime is used but never imported
            out["save_note"] = f"{type(e).__name__}: {e}"

        seen = []

        async def fake(messages):
            seen.append(messages[-1]["content"])
            return "not json"

        chat._provider_chat = fake
        raw_model_output = "Sure! The tool is WEATHER."
        try:
            chat._parse_tool_router_result(raw_model_output)
        except Exception as exc:
            asyncio.run(chat._retry_fix_json(str(exc)))  # exactly how /chat calls it
        out["repair_prompt_contains_model_output"] = raw_model_output in seen[0]
        out["repair_prompt_excerpt"] = seen[0][:230]
    p = ROOT / "bench" / "results" / "v1_bugs.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
