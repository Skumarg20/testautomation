"""
One Test Studio browser run in its own process (server mode).

The server starts it with the MargBooks login of the QA who pressed Run in this process's environment
(STUDIO_RUN_CREDS=1, MARGBOOKS_USER, MARGBOOKS_PASS), so two QAs' runs never share a login, a browser or the
framework's process-wide state (settings, safety logs, Control Room change list).

stdin : {"cases": [...], "opts": {...}}               (JSON)
stdout: lines "@@STUDIO@@ {json}" with
        {"ev": "step", "ci", "si", "status", "secs", "shot"}  |  {"ev": "log", "m"}  |  {"ev": "result", "results"}
        Everything else on stdout/stderr is the framework's own console output (kept in the run log).
"""
from __future__ import annotations

import json
import os
import sys

MARK = "@@STUDIO@@ "


def _emit(obj: dict):
    sys.stdout.write(MARK + json.dumps(obj, default=str) + "\n")
    sys.stdout.flush()


def stop_event(path: str | None, poll: float = 0.5):
    """A threading.Event that is set when the server creates the stop file (STUDIO_STOP_FILE). The run then stops
    at its next step the same way a local run does: clean-up steps and the setting undo still run."""
    import threading
    import time
    ev = threading.Event()
    if not path:
        return ev

    def _poll():
        while not ev.is_set():
            if os.path.exists(path):
                ev.set()
                return
            time.sleep(poll)
    threading.Thread(target=_poll, daemon=True).start()
    return ev


def main() -> int:
    os.environ.setdefault("HEADLESS", "true")
    job = json.loads(sys.stdin.read() or "{}")
    stop = stop_event(os.environ.get("STUDIO_STOP_FILE"))
    from ui_studio import executor
    try:
        res = executor._play(job.get("cases") or [], job.get("opts") or {},
                             lambda ci, si, st, secs, shot: _emit({"ev": "step", "ci": ci, "si": si, "status": st,
                                                                   "secs": secs, "shot": shot}),
                             lambda m: _emit({"ev": "log", "m": str(m)}), stop)
    except Exception as e:  # noqa: BLE001  (the server shows the reason in plain words, the traceback goes to the log)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        _emit({"ev": "error", "kind": type(e).__name__, "m": str(e)[:600]})
        return 1
    _emit({"ev": "result", "results": res})
    return 0


if __name__ == "__main__":
    sys.exit(main())
