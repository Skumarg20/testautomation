"""
Crawl ke dauraan pehra ON rehna chahiye -- browser ke bina.

ASLI KHATRA: --enable ke liye ALLOW_DESTRUCTIVE=true chahiye tha, aur wahi flag
click-guard aur delete-request block ko bhi band kar deta tha. Yaani poore crawl
me, list pages ke trash icons ke saath, koi pehra nahi tha.

Ab "Control Room ki setting badalna theek hai" ek alag flag hai.
"""
import inspect

import pytest

from config.settings import settings
from framework import control_room as cr
from framework import safety


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_DESTRUCTIVE", False)
    cr.allow_settings_change(False)
    yield
    cr.allow_settings_change(False)


class _Sentinel(Exception):
    pass


def test_bina_ijazat_setting_badalna_roka_jata_hai():
    with pytest.raises(cr.SettingLocked):
        cr.enable_yes(object(), verbose=False)


def test_alag_flag_se_setting_badalne_ki_ijazat_milti_hai(monkeypatch):
    """Flag ON ho to SettingLocked nahi aata -- aage Control Room kholne tak pahunchta hai."""
    def boom(*_a, **_k):
        raise _Sentinel
    monkeypatch.setattr(cr, "open_control_room", boom)
    cr.allow_settings_change(True)
    with pytest.raises(_Sentinel):
        cr.enable_yes(object(), verbose=False)
    assert settings.ALLOW_DESTRUCTIVE is False, "flag ne guard band kar diya"


def test_restore_bhi_alag_flag_se_chalta_hai(monkeypatch):
    import json
    import tempfile
    import pathlib
    tmp = pathlib.Path(tempfile.mkdtemp()) / "b.json"
    tmp.write_text(json.dumps({"saved_at": "x", "settings": []}))
    monkeypatch.setattr(cr, "BACKUP", tmp)

    def boom(*_a, **_k):
        raise _Sentinel
    monkeypatch.setattr(cr, "open_control_room", boom)
    with pytest.raises(cr.SettingLocked):
        cr.restore(object(), verbose=False)
    cr.allow_settings_change(True)
    with pytest.raises(_Sentinel):
        cr.restore(object(), verbose=False)


def test_flag_ke_saath_bhi_delete_button_block_hota_hai():
    """Setting badalne ki ijazat ka matlab ye nahi ki trash icon dabana theek hai."""
    class Loc:
        def evaluate(self, _js):
            return {"tag": "button", "id": "Griddeletetbtn1", "cls": "mksBtn del",
                    "title": "", "aria": "", "text": "", "disarmed": False}
    cr.allow_settings_change(True)
    with pytest.raises(safety.UnsafeClick):
        safety.assert_safe(Loc(), "crawl")


def test_flag_ke_saath_netguard_delete_request_rokta_hai():
    from framework import netguard

    class R:
        method = "DELETE"
        url = "https://books4.margbooks.com/api/ledger/12"
    cr.allow_settings_change(True)
    assert netguard._is_delete(R()) is True


def test_crawler_enable_me_bhi_ALLOW_DESTRUCTIVE_False_rakhta_hai():
    from framework import run_crawler
    src = inspect.getsource(run_crawler.main)
    i = src.index("--enable: Control Room")
    block = src[i:i + 700]
    assert "ALLOW_DESTRUCTIVE = False" in block
    assert "allow_settings_change(True)" in block


def test_restore_settings_bhi_guard_ON_rakhta_hai():
    from framework import restore_settings
    src = inspect.getsource(restore_settings.main)
    assert "ALLOW_DESTRUCTIVE = False" in src and "allow_settings_change(True)" in src
    # Ijazat ki jaanch (user ne Allow writes diya?) guard band karne se PEHLE
    assert src.index("if not settings.ALLOW_DESTRUCTIVE") < src.index("ALLOW_DESTRUCTIVE = False")


def test_flag_sirf_Control_Room_ke_teen_kaamon_me_padha_jata_hai():
    """Aur kisi jagah (save, form) ye flag ijazat na bane."""
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent
    users = []
    for f in list((root / "framework").glob("*.py")) + list((root / "pages").glob("*.py")):
        if "SETTINGS_WRITE_OK" in f.read_text(encoding="utf-8"):
            users.append(f.name)
    assert users == ["control_room.py"], users
    src = (root / "framework" / "control_room.py").read_text(encoding="utf-8")
    assert len(re.findall(r"SETTINGS_WRITE_OK", src)) == 6   # def, global, 1 set, 3 checks
