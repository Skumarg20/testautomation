"""testcases/*.yaml load + validate karta hai."""
from __future__ import annotations

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
    """
    folder = folder or settings.TESTCASES
    cases: list[TestCase] = []
    seen: set[str] = set()
    for f in sorted(folder.rglob("*.yaml")):
        docs = yaml.safe_load(f.read_text()) or []
        for raw in docs:
            missing = [k for k in REQUIRED if k not in raw]
            if missing:
                raise ValueError(f"{f.name}: case missing {missing}: {raw.get('id', '?')}")
            if raw["id"] in seen:
                raise ValueError(f"Duplicate test case id: {raw['id']}")
            seen.add(raw["id"])
            rel = f.relative_to(folder).as_posix()
            cases.append(TestCase(source_file=rel, **raw))
    return cases
