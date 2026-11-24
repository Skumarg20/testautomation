"""
Merge verified cases (artifacts/verify/cases/<ID>.yaml) back into their source files, and count verdicts.

    python -m tools.verify_merge            # report only
    python -m tools.verify_merge --write    # also replace the cases in testcases/trades|library/*.yaml

A source case is replaced only by a verified copy that loads, has the same id, and a verification block.
Backups of every changed source file go to artifacts/verify/backups/<time>/.
"""
from __future__ import annotations

import argparse
import collections
import shutil
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "artifacts" / "verify" / "cases"
SOURCES = [ROOT / "testcases" / "trades", ROOT / "testcases" / "library"]
VERDICTS = ("verified", "corrected", "app_defect", "blocked", "not_applicable")


def load_verified() -> tuple[dict, list[str]]:
    out, problems = {}, []
    for f in sorted(CASES.glob("*.yaml")):
        try:
            d = yaml.safe_load(f.read_text(encoding="utf-8"))
            c = d[0] if isinstance(d, list) else d
            v = (c or {}).get("verification") or {}
            if c.get("id") != f.stem:
                problems.append(f"{f.name}: id {c.get('id')!r} does not match the file name")
            elif v.get("status") not in VERDICTS:
                problems.append(f"{f.name}: verification.status {v.get('status')!r}")
            else:
                out[c["id"]] = c
        except Exception as e:  # noqa: BLE001
            problems.append(f"{f.name}: {type(e).__name__}: {e}"[:200])
    return out, problems


def _for_suite(case: dict) -> dict:
    """Mark a verified copy for the full run: tag 'passed' (verified/corrected, steps pass),
    'app_defect' (+ known_issue, steps fail on purpose), blocked/not_applicable stay out of the run (draft)."""
    c = dict(case)
    st = c["verification"]["status"]
    tags = [t for t in (c.get("tags") or []) if t not in ("passed", "app_defect", "blocked", "not_applicable")]
    if st in ("verified", "corrected") and c.get("steps"):
        tags.append("passed")
    elif st == "app_defect":
        tags.append("app_defect")
        c["known_issue"] = True
    else:
        tags.append(st)
        c["draft"] = True
    c["tags"] = tags
    return c


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    ver, problems = load_verified()
    total, seen = 0, set()
    by_file: dict[Path, list] = {}
    for folder in SOURCES:
        for f in sorted(folder.glob("*.yaml")):
            data = yaml.load(f.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader) or []
            by_file[f] = data
            for c in data:
                if isinstance(c, dict) and c.get("id"):
                    total += 1
                    seen.add(c["id"])
    counts = collections.Counter(c["verification"]["status"] for c in ver.values())
    runnable = sum(1 for c in ver.values() if c.get("steps") and c["verification"]["status"] in ("verified", "corrected"))
    print(f"{len(ver)} of {total} cases verified in the app ({total - len(ver)} to go)")
    for k in VERDICTS:
        print(f"  {k:15s} {counts.get(k, 0)}")
    print(f"  runnable scripts (steps pass): {runnable}")
    orphans = sorted(set(ver) - seen)
    if orphans:
        print(f"  {len(orphans)} verified ids not in any source file: {orphans[:10]}")
    for p in problems:
        print("  PROBLEM", p)
    if not a.write:
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    changed = 0
    for f, data in by_file.items():
        hit = [i for i, c in enumerate(data) if isinstance(c, dict) and c.get("id") in ver]
        if not hit:
            continue
        bk = ROOT / "artifacts" / "verify" / "backups" / stamp
        bk.mkdir(parents=True, exist_ok=True)
        shutil.copy(f, bk / f.name)
        for i in hit:
            data[i] = _for_suite(ver[data[i]["id"]])
        f.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8")
        changed += len(hit)
    print(f"wrote {changed} cases into their source files (backup: artifacts/verify/backups/{stamp})")


if __name__ == "__main__":
    main()
