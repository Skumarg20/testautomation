"""
Locator store with self-healing.

MargBooks ka DOM humein pehle se pata nahi hai, aur Marg apna UI update karta
rehta hai. Isliye har logical element ke liye hum ek *list* of candidate
selectors rakhte hain. Resolver pehla wala try karta hai; fail ho to agla.
Jo chala, use list ke top pe promote kar diya jata hai aur file wapas likh di
jati hai -- yani suite khud ko heal karti rehti hai.
"""
from __future__ import annotations

import threading
import yaml
from pathlib import Path
from typing import Any

from config.settings import settings

_lock = threading.Lock()


class LocatorNotFound(Exception):
    pass


class LocatorStore:
    def __init__(self, path: Path | None = None):
        self.path = path or settings.LOCATOR_FILE
        self._data: dict[str, Any] = {}
        self._dirty = False
        self.load()

    def load(self):
        if self.path.exists():
            self._data = yaml.safe_load(self.path.read_text()) or {}
        else:
            self._data = {}

    def save(self):
        if not self._dirty:
            return
        with _lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                yaml.safe_dump(self._data, sort_keys=False, allow_unicode=True)
            )
            self._dirty = False

    def candidates(self, key: str) -> list[str]:
        """key format: 'page.element', e.g. 'login.username'"""
        page, _, element = key.partition(".")
        node = self._data.get(page, {}).get(element)
        if node is None:
            raise LocatorNotFound(
                f"'{key}' locators file me nahi hai. "
                f"`python -m agent.discover --page {page}` chalao ya manually add karo."
            )
        return node if isinstance(node, list) else [node]

    def promote(self, key: str, selector: str):
        """Jo selector chala use top pe le aao."""
        page, _, element = key.partition(".")
        node = self._data.get(page, {}).get(element)
        if not isinstance(node, list) or node[0] == selector:
            return
        node.remove(selector)
        node.insert(0, selector)
        self._dirty = True

    def add(self, key: str, selectors: list[str]):
        page, _, element = key.partition(".")
        self._data.setdefault(page, {})[element] = selectors
        self._dirty = True

    def all_keys(self) -> list[str]:
        return [f"{p}.{e}" for p, els in self._data.items() for e in els]


store = LocatorStore()
