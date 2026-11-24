"""
Tests asli locators/margbooks.yaml ko kabhi na chhuyein.

autolearn ke test `store.add(...)` + `store.save()` karte the, aur wo seedha
asli file me likh jata tha -- `t:` section me btnSave27 jaisa kachra isi se aaya
(wo id har tab me badalti hai, locator ke kaam ki nahi). Har test apni alag copy
par chalta hai aur khatam hote hi memory ki haalat bhi wapas.
"""
import copy
import shutil

import pytest


@pytest.fixture(autouse=True)
def _no_real_ai(monkeypatch):
    """Unit tests never call a real AI (paid, slow, different every run).

    Once the AI key in .env worked, tests of the "not understood" fallback started getting a live model's
    wording instead. With no key no provider is active, so ai.ask never reaches the network; tests of the
    provider functions themselves fake the HTTP layer, and a test that needs AI behaviour sets its own fake
    (e.g. monkeypatch ai.available / ai.ask_json), which replaces this one.
    """
    from framework import ai

    monkeypatch.setattr(ai, "gemini_key", lambda *a, **k: "")
    monkeypatch.setattr(ai, "anthropic_key", lambda *a, **k: "")


@pytest.fixture(autouse=True)
def _isolated_locator_store(tmp_path, monkeypatch):
    from framework.locator_store import store
    tmp = tmp_path / "margbooks.yaml"
    if store.path.exists():
        shutil.copy(store.path, tmp)
    before = copy.deepcopy(store._data)
    dirty = store._dirty
    monkeypatch.setattr(store, "path", tmp)
    yield
    store._data = before
    store._dirty = dirty
