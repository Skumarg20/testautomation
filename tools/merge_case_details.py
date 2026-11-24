"""
Merge the detailed manual steps written per batch (artifacts/case_details/out/bNNN.json) into config/case_details.json,
which the Test cases screen reads (ui_studio/tests.py: case_details()).

Every entry is checked before it is taken:
  * its case id is one of the batch's input ids (artifacts/case_details/in/bNNN.json);
  * steps is a non-empty list of text; preconditions / expected / refs are lists of text;
  * no MargBooks password, e-mail address or 10-digit mobile number is in it (customer data must never be copied
    from Jira / support records into test steps).
A bad entry is reported and left out; the rest of its batch is still taken.

    python -m tools.merge_case_details            # check and show what would change
    python -m tools.merge_case_details --apply    # write config/case_details.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "artifacts" / "case_details" / "in"
OUT_DIR = ROOT / "artifacts" / "case_details" / "out"
TARGET = ROOT / "config" / "case_details.json"

EMAIL = re.compile(r"[\w.+-]+@[A-Za-z][\w-]*\.[A-Za-z][\w.]+")    # not a POS "barcode@qty" like 000003@0.35
MOBILE = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")
SAFE_EMAIL = re.compile(r"@(?:margbooks-qa\.invalid|example\.(?:com|org|net)|abdm)\b|qa_|test", re.I)
LIST_KEYS = ("preconditions", "steps", "expected", "refs")
# Made-up test numbers the steps type into a mobile field (a mobile field needs 10 digits starting 6-9), and
# MargBooks' own published support addresses. Anything else that looks like a person's contact is refused.
SAFE_MOBILE = re.compile(r"^(?:9876543210|98765\d{5}|90000\d{5}|9999999999|9988776655"
                         r"|8010971097)$")         # 8010971097: MargBooks' own "missed call for demo" number
SAFE_DOMAIN = re.compile(r"@margbooks\.com$", re.I)


def _secrets() -> list[str]:
    vals = []
    try:
        from config.settings import settings
        vals += [settings.PASSWORD, settings.PIN]
    except Exception:  # noqa: BLE001
        pass
    try:
        envs = json.loads((ROOT / "config" / "environments.json").read_text(encoding="utf-8"))
        for e in (envs.get("envs") or {}).values():
            vals.append(e.get("password"))
    except Exception:  # noqa: BLE001
        pass
    return [v for v in vals if isinstance(v, str) and len(v) > 3]


def check_entry(cid: str, e, secrets: list[str]) -> list[str]:
    if not isinstance(e, dict):
        return ["not an object"]
    bad = []
    for k in LIST_KEYS:
        v = e.get(k, [])
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            bad.append(f"{k} is not a list of text")
    if not bad and not [s for s in e.get("steps") or [] if s.strip()]:
        bad.append("no steps")
    text = json.dumps(e, ensure_ascii=False)
    if any(s in text for s in secrets):
        bad.append("contains a MargBooks password")
    for m in EMAIL.finditer(text):
        if not SAFE_EMAIL.search(m.group()) and not SAFE_DOMAIN.search(m.group()):
            bad.append(f"e-mail address {m.group()!r}")
    for mm in MOBILE.finditer(text):
        if not SAFE_MOBILE.match(mm.group()):
            bad.append(f"mobile number {mm.group()!r}")
    return bad


def clean(e: dict) -> dict:
    out = {k: [x.strip() for x in e.get(k) or [] if x.strip()] for k in LIST_KEYS}
    out["checked_live"] = bool(e.get("checked_live"))
    out["written_by"] = str(e.get("written_by") or "Claude agent (from code, specs and docs)")[:120]
    out["updated"] = str(e.get("updated") or "")[:20]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    secrets = _secrets()
    current = json.loads(TARGET.read_text(encoding="utf-8")) if TARGET.exists() else {}
    taken, problems, missing_files, missing_ids = {}, [], [], []
    for fin in sorted(IN_DIR.glob("b*.json")):
        want = [c["id"] for c in json.loads(fin.read_text(encoding="utf-8"))]
        fout = OUT_DIR / fin.name
        if not fout.exists():
            missing_files.append(fin.stem)
            continue
        try:
            got = json.loads(fout.read_text(encoding="utf-8"))
        except ValueError as e:
            problems.append(f"{fin.stem}: not valid JSON ({e})")
            continue
        if not isinstance(got, dict):
            problems.append(f"{fin.stem}: not an object")
            continue
        for cid in want:
            if cid not in got:
                missing_ids.append(cid)
                continue
            bad = check_entry(cid, got[cid], secrets)
            if bad:
                problems.append(f"{fin.stem} {cid}: {'; '.join(bad)}")
            else:
                taken[cid] = clean(got[cid])
        extra = sorted(set(got) - set(want))
        if extra:
            problems.append(f"{fin.stem}: ids not in its input, ignored: {', '.join(extra[:5])}")
    new = sum(1 for k in taken if k not in current)
    print(f"entries ok: {len(taken)} ({new} new, {len(taken) - new} replaced)")
    print(f"batches without output: {len(missing_files)} {' '.join(missing_files)}")
    print(f"ids missing from their output: {len(missing_ids)} {' '.join(missing_ids[:20])}")
    print(f"problems: {len(problems)}")
    for p in problems[:60]:
        print("  ", p)
    if a.apply and taken:
        merged = {**current, **taken}
        TARGET.write_text(json.dumps(merged, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"written: {TARGET} ({len(merged)} cases)")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
