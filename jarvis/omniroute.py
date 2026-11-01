"""Start OmniRoute when Jarvis needs it, and stop it on exit only if Jarvis was the one that started it.

    external   an OmniRoute was already answering, so Jarvis leaves it alone (never stops it)
    starting   Jarvis launched `omniroute serve` and is waiting for it to answer
    started    Jarvis launched it and it is healthy; it will be stopped when Jarvis exits
    failed     it could not be started (not installed, crashed, or too slow); general questions explain why
    remote     the endpoint is not on this machine, so there is nothing to start
    off        no endpoint configured, or JARVIS_MANAGE_OMNIROUTE=0

On Windows the child is placed in a job object that kills it when Jarvis exits for any reason, including
closing the console window or killing jarvis.exe, so it cannot be left behind by accident.
"""

import atexit
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

LOCAL = {"localhost", "127.0.0.1", "::1", "[::1]"}
READY_TIMEOUT_S = float(os.getenv("OMNIROUTE_READY_TIMEOUT_S", "90"))


def _kill_on_close_job(proc: subprocess.Popen):
    """Windows only: tie the child's lifetime to this process. Returns the job handle (keep it referenced)."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class Io(ctypes.Structure):
        _fields_ = [(n, ctypes.c_uint64) for n in ("r", "w", "o", "rb", "wb", "ob")]

    class Extended(ctypes.Structure):
        _fields_ = [("Basic", Basic), ("Io", Io), ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateJobObjectW.restype = wintypes.HANDLE
    k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    job = k.CreateJobObjectW(None, None)
    if not job:
        return None
    info = Extended()
    info.Basic.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    k.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
    k.AssignProcessToJobObject(job, wintypes.HANDLE(int(proc._handle)))
    return job


class OmniRoute:
    def __init__(self) -> None:
        self.state = "off"
        self.detail = ""
        self.proc: subprocess.Popen | None = None
        self._job = None
        self._lock = threading.Lock()
        atexit.register(self.stop)

    # ---- helpers ----
    @staticmethod
    def _target(endpoint: str) -> tuple[str, int, str] | None:
        u = urlparse(endpoint)
        if not u.hostname:
            return None
        return u.hostname, u.port or (443 if u.scheme == "https" else 80), f"{u.scheme}://{u.netloc}"

    @staticmethod
    def healthy(base: str, timeout: float = 1.5) -> bool:
        try:
            return httpx.get(base + "/api/health", timeout=timeout).status_code == 200
        except httpx.HTTPError:
            return False

    @staticmethod
    def executable() -> str | None:
        return os.getenv("OMNIROUTE_BIN") or shutil.which("omniroute")

    # ---- lifecycle ----
    def ensure(self, endpoint: str) -> None:
        """Make sure something answers at the endpoint. Blocking, so run it in a thread."""
        if os.getenv("JARVIS_MANAGE_OMNIROUTE", "1") == "0" or not endpoint:
            self.state = "off"
            return
        target = self._target(endpoint)
        if not target:
            self.state = "off"
            return
        host, port, base = target
        if host not in LOCAL:
            self.state, self.detail = "remote", host
            return
        if self.healthy(base):
            self.state, self.detail = "external", f"already running on port {port}"
            return
        exe = self.executable()
        if not exe:
            self.state, self.detail = "failed", "OmniRoute is not installed (npm install -g omniroute)"
            return
        with self._lock:
            self.state, self.detail = "starting", f"launching OmniRoute on port {port}"
            cmd = [exe, "serve", "--no-open", "--no-tray", "--port", str(port)]
            flags = (subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0
            try:
                self.proc = subprocess.Popen(cmd, cwd=str(Path.home()), stdin=subprocess.DEVNULL,
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                             creationflags=flags, start_new_session=os.name != "nt")
            except OSError as exc:
                self.state, self.detail = "failed", f"could not start OmniRoute: {exc}"
                return
            self._job = _kill_on_close_job(self.proc)
        deadline = time.monotonic() + READY_TIMEOUT_S
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                self.state, self.detail = "failed", f"OmniRoute exited with code {self.proc.returncode}"
                return
            if self.healthy(base):
                self.state, self.detail = "started", f"started by Jarvis on port {port}"
                return
            time.sleep(1)
        self.state, self.detail = "failed", f"OmniRoute did not answer within {int(READY_TIMEOUT_S)} s"
        self.stop()

    def stop(self) -> None:
        """Stop OmniRoute, but only a copy this object started."""
        with self._lock:
            p, self.proc = self.proc, None
        if not p or p.poll() is not None:
            return
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True, check=False)
        else:
            import signal

            try:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
        if self.state in ("started", "starting"):
            self.state, self.detail = "off", "stopped"

    def ensure_in_background(self, endpoint: str) -> None:
        threading.Thread(target=self.ensure, args=(endpoint,), name="omniroute", daemon=True).start()


manager = OmniRoute()

