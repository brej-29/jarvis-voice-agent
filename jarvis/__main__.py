"""`python -m jarvis` (or jarvis.exe): start the local server and open the browser."""

import argparse
import threading
import webbrowser

import uvicorn


def main():
    ap = argparse.ArgumentParser(prog="jarvis")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    if not a.no_browser:
        threading.Timer(1.5, webbrowser.open, args=(f"http://{a.host}:{a.port}",)).start()
    from jarvis.server import app

    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
