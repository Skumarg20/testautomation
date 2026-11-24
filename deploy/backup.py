"""Back up everything the team made: users and run history (studio.db), test cases, locators, settings, QA data.

    .venv\\Scripts\\python deploy\\backup.py [backup folder]        (default: backups\\ next to this project)

The database is copied with SQLite's own online backup, so it is consistent also while the Studio runs. Each backup
is a dated folder; the newest 14 are kept. Run it daily (deploy\\backup.bat from Windows Task Scheduler).
Run screenshots / videos (artifacts\\) are not included: they are large and can be made again.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEEP = 14
FOLDERS = ["testcases", "locators", "config/qa_baseline"]
FILES = ["config/environments.json", "config/qa_data.json", "config/case_details.json", "config/e2e_company_map.json",
         "config/studio_settings.json", "config/studio_aliases.json", "config/control_room.json", ".env",
         "e2e_scripts/.env"]


def backup(dest_root: Path) -> Path:
    dest = dest_root / time.strftime("%Y-%m-%d_%H%M")
    (dest / "config").mkdir(parents=True, exist_ok=True)
    db = ROOT / "config" / "studio.db"
    if db.exists():
        src = sqlite3.connect(db, timeout=60)
        out = sqlite3.connect(dest / "config" / "studio.db")
        with out:
            src.backup(out)
        out.close()
        src.close()
    for f in FILES:
        p = ROOT / f
        if p.exists():
            (dest / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest / f)
    for d in FOLDERS:
        p = ROOT / d
        if p.exists():
            shutil.copytree(p, dest / d, dirs_exist_ok=True)
    old = sorted((x for x in dest_root.iterdir() if x.is_dir()), key=lambda x: x.name)
    for x in old[:-KEEP]:
        shutil.rmtree(x, ignore_errors=True)
    return dest


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "backups"
    print(f"Backup written: {backup(target)}")
