"""Build the static site for GitHub Pages: the UI plus the int8 router, which then runs in the browser.

    python packaging/build_pages.py site
"""

import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = Path(sys.argv[1] if len(sys.argv) > 1 else "site")
shutil.rmtree(out, ignore_errors=True)  # may fail if a server is running inside it; copytree below overwrites
shutil.copytree(root / "jarvis" / "web", out, dirs_exist_ok=True)
(out / "model").mkdir(exist_ok=True)
for name in ("model.int8.onnx", "tokenizer.json", "meta.json"):
    shutil.copy(root / "models" / "joint" / name, out / "model" / name)
(out / "config.js").write_text("window.JARVIS_STATIC = true;\n", encoding="utf-8")
(out / ".nojekyll").write_text("", encoding="utf-8")
print("built", out)
