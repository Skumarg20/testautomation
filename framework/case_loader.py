"""testcases/*.yaml load + validate karta hai."""
from __future__ import annotations

import threading

import yaml
from dataclasses import dataclass
from pathlib import Path

from config.settings import settings

REQUIRED = ("id", "module", "title", "steps")


@dataclass
class TestCase:
    id: str
    module: str
    title: str
    steps: list[dict]
    priority: str = "p2"
    tags: list[str] = None
    preconditions: list[str] = None
    expected: list[str] = None
    destructive: bool = False
    draft: bool = False
    known_issue: bool = False
    verification: dict = None          # live-app check result (artifacts/verify/cases, merged by tools.verify_merge)
    source_file: str = ""

    @property
    def screens(self) -> list[str]:
        """Ye test kaunsi screen chhoota hai."""
        out = []
        for st in self.steps:
            if st.get("action") == "open_screen" and st.get("target"):
                out.append(st["target"])
            elif st.get("action") == "goto" and st.get("target"):
                from framework.screens import SCREENS
                url = str(st["target"])
                for k, cfg in SCREENS.items():
                    if cfg.get("url") and cfg["url"] == url:
                        out.append(k)
        return list(dict.fromkeys(out))

    @property
    def menu(self) -> str:
        """
        Test ka menu rasta -- 'Sale > Bill'.

        Tester ke dimaag me flat module nahi, sidebar hota hai. Isliye test
        bhi usi dhaanche me dikhne chahiye.
        """
        from framework import menu_tree
        for sc in self.screens:
            path = menu_tree.menu_of_screen(sc)
            if path:
                return path
        return ""

    @property
    def menu_id(self) -> str:
        from framework import menu_tree
        for sc in self.screens:
            node = menu_tree.node_for_screen(sc)
            if node:
                return node["id"]
        return ""

    @property
    def marks(self) -> list[str]:
        m = set(self.tags or [])
        m.add(self.priority.lower())
        m.add(self.module.lower())
        if self.destructive:
            m.add("destructive")
        if self.draft:
            m.add("draft")
        if self.known_issue:
            m.add("known_issue")
        return sorted(m)


def load_all(folder: Path | None = None) -> list[TestCase]:
    """
    Saare test case load karo -- testcases/ aur uske andar ke folder bhi.

    saved/ folder me UI se banaye test rehte hain. Pehle sirf testcases/*.yaml
    padhta tha, isliye UI se save kiya test list me aata hi nahi tha.

    Test Studio calls this on every request. Parsing 3,000+ YAML files takes many seconds, so every file's cases
    are kept until THAT file changes: a save from the UI re-parses one file, not all of them. One rebuild at a
    time (a lock), so requests that arrive during it wait for it instead of each parsing everything again.
    """
    folder = folder or settings.TESTCASES
    with _LOCK:
        sigs = []
        for f in sorted(folder.rglob("*.yaml")):
            try:
                st = f.stat()
            except FileNotFoundError:      # removed between listing and stat (a test's temp case): skip it
                continue
            sigs.append((f, (st.st_mtime_ns, st.st_size)))
        key = (str(folder), tuple((str(f), sig) for f, sig in sigs))
        if _CACHE.get("key") == key:
            return list(_CACHE["cases"])
        per = _CACHE.get("per") if _CACHE.get("folder") == str(folder) else None
        if per is None:
            per = _disk_get(folder) or {}
        new_per, changed = {}, False
        for f, sig in sigs:
            hit = per.get(str(f))
            if hit is not None and hit[0] == sig:
                new_per[str(f)] = hit
                continue
            got = _parse_file(folder, f)
            changed = True
            if got is not None:
                new_per[str(f)] = (sig, got)
        changed = changed or len(new_per) != len(per)
        cases: list[TestCase] = []
        seen: set[str] = set()
        for f, _ in sigs:
            for c in (new_per.get(str(f)) or (None, []))[1]:
                if c.id in seen:
                    raise ValueError(f"Duplicate test case id: {c.id}")
                seen.add(c.id)
                cases.append(c)
        if changed:
            _disk_put(folder, new_per)
        _CACHE.update(key=key, cases=cases, per=new_per, folder=str(folder))
        return list(cases)


def cache_key():
    """Changes whenever load_all() returned different cases (for callers that cache what they build from them)."""
    k = _CACHE.get("key")
    return hash(k) if k is not None else None


_DISK = settings.TESTCASES.parent / "artifacts" / ".cache" / "cases.pkl"
_DISK_VERSION = 2


def _disk_get(folder: Path):
    """Each file's parsed cases from the last process (saves ~3 s on every start); only changed files re-parse."""
    import pickle
    try:
        with open(_DISK, "rb") as fh:
            v, fold, per = pickle.load(fh)
        return per if v == _DISK_VERSION and fold == str(folder) and isinstance(per, dict) else None
    except Exception:  # noqa: BLE001  (missing, stale format, partial write)
        return None


def _disk_put(folder: Path, per: dict) -> None:
    import os, pickle
    try:
        _DISK.parent.mkdir(parents=True, exist_ok=True)
        tmp = _DISK.with_suffix(f".{os.getpid()}.tmp")
        with open(tmp, "wb") as fh:
            pickle.dump((_DISK_VERSION, str(folder), per), fh, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, _DISK)
    except Exception:  # noqa: BLE001
        pass


_CACHE: dict = {}
_LOCK = threading.RLock()
_Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)      # libyaml when installed: ~10x faster


def _parse_file(folder: Path, f: Path) -> list[TestCase] | None:
    """The cases of one YAML file; None when the file is gone."""
    try:
        text = f.read_text(encoding="utf-8")
    except FileNotFoundError:          # removed between listing and reading (a test's temp case): skip it
        return None
    out: list[TestCase] = []
    rel = f.relative_to(folder).as_posix()
    for raw in yaml.load(text, Loader=_Loader) or []:
        missing = [k for k in REQUIRED if k not in raw]
        if missing:
            raise ValueError(f"{f.name}: case missing {missing}: {raw.get('id', '?')}")
        out.append(TestCase(source_file=rel, **raw))
    return out


def _parse(folder: Path, files: list[Path]) -> list[TestCase]:
    cases: list[TestCase] = []
    seen: set[str] = set()
    for f in files:
        for c in _parse_file(folder, f) or []:
            if c.id in seen:
                raise ValueError(f"Duplicate test case id: {c.id}")
            seen.add(c.id)
            cases.append(c)
    return cases
