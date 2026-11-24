"""
How this Test Studio runs.

  local  (default): one tester on their own PC; http://127.0.0.1:8778, no Studio login, the shared environment's
                    MargBooks login, one browser at a time, Record opens Playwright codegen on this PC.
  server          : one Studio for the QA team, opened in the browser. Studio login for every page and call,
                    each QA runs with their own MargBooks login, every run in its own process, a run queue.

Environment variables (server):
  STUDIO_MODE=server
  STUDIO_HOST=0.0.0.0            address to listen on (put HTTPS in front: see ui_studio/DEPLOY.md)
  STUDIO_PORT=8778
  STUDIO_MAX_BROWSERS=3          browsers running at the same time on this machine (RAM: ~600 MB each)
  STUDIO_SECURE_COOKIE=1         when users reach the Studio through HTTPS (recommended)
  STUDIO_KEEP_RUN_DAYS=30        run folders (screenshots, video, trace) older than this are deleted;
                                 0 (or less) keeps them forever. A folder younger than a day is never deleted.
"""
from __future__ import annotations

import os


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


SERVER = os.environ.get("STUDIO_MODE", "local").strip().lower() == "server"
HOST = os.environ.get("STUDIO_HOST", "0.0.0.0" if SERVER else "127.0.0.1")
PORT = _int("STUDIO_PORT", 8778)
MAX_BROWSERS = max(1, _int("STUDIO_MAX_BROWSERS", 3)) if SERVER else 1
SECURE_COOKIE = os.environ.get("STUDIO_SECURE_COOKIE", "") == "1"
KEEP_RUN_DAYS = max(0, _int("STUDIO_KEEP_RUN_DAYS", 30))      # 0: keep forever
