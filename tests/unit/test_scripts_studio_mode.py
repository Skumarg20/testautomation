"""Python scripts run like Studio tests: the environment, login and company of Settings, writes only in QA companies."""
import json

import pytest

from ui_studio import e2e, qa_ids


def test_company_list_gives_only_qa_company_ids():
    reply = {"Data": [{"compname": "QA Chemist", "linkid": 7145375269391}, {"compname": "Real Pharma", "linkid": 1},
                      {"compname": "QA Garment", "linkid": 0}]}
    assert qa_ids.ids_from_company_list(reply) == {"QA Chemist": "7145375269391"}
    assert qa_ids.ids_from_company_list({"Data": {"list": reply["Data"]}}) == {"QA Chemist": "7145375269391"}
    assert qa_ids.ids_from_company_list(None) == {}


@pytest.fixture
def env_settings(monkeypatch, tmp_path):
    from ui import envs
    active = {"app_url": "https://books6.margbooks.com/", "login_url": "https://books6.margbooks.com/login",
              "user": "u@x.in", "password": "Pw#12345", "company": "CHEMIST AUTOMATION (AGENT)", "allow_writes": True}
    monkeypatch.setattr(envs, "apply_active", lambda: dict(active))
    monkeypatch.setattr(qa_ids, "get", lambda url: {"QA Chemist": "111", "QA Garment": "222"})
    monkeypatch.setattr(qa_ids, "login_page", lambda url: "https://margbooks.com/login/")
    monkeypatch.setattr(e2e, "COMPANY_MAP", tmp_path / "none.json")
    return active


def test_studio_env_points_the_scripts_at_settings_with_the_guard(env_settings):
    env = e2e.studio_env()
    assert env["STUDIO_QA_GUARD"] == "1" and env["MARGBOOKS_QA_URL"] == "https://books6.margbooks.com"
    assert env["MARGBOOKS_LOGIN_URL"] == "https://margbooks.com/login/"
    assert set(env["STUDIO_TARGET_HOSTS"].split(",")) == {"books6.margbooks.com", "margbooks.com"}
    assert set(env["STUDIO_QA_COMPLINKIDS"].split(",")) == {"111", "222"}
    assert env["STUDIO_DEFAULT_COMPANY"] == "QA Chemist"            # the Settings company is not a QA company
    assert env["QA_CHEMIST_USER"] == "u@x.in" and env["QA_PHARMA_PASS"] == "Pw#12345"
    assert json.loads(env["STUDIO_COMPANY_MAP"])["Garments New 29-08"] == "QA Garment"


def test_writes_off_in_settings_means_no_company_may_be_written(env_settings, monkeypatch):
    from ui import envs
    monkeypatch.setattr(envs, "apply_active", lambda: {**env_settings, "allow_writes": False, "company": "QA Garment"})
    env = e2e.studio_env()
    assert env["STUDIO_QA_COMPLINKIDS"] == "" and env["STUDIO_DEFAULT_COMPANY"] == "QA Garment"


def test_team_mode_uses_the_qas_own_login(env_settings):
    env = e2e.studio_env({"mb_user": "qa7@x.in", "mb_password": "Own#Pass9", "username": "qa7@qa.test"})
    assert env["QA_CHEMIST_USER"] == "qa7@x.in" and env["QA_ADMIN_PASS"] == "Own#Pass9"


def test_guard_block_is_explained():
    assert "QA guard stopped" in e2e.explain(["[studio-guard] BLOCKED POST https://x/Save: a write in company 9"])


def test_live_steps_are_read_and_only_step_screenshots_are_served(tmp_path, monkeypatch):
    (tmp_path / "steps.jsonl").write_text(
        '{"n": 1, "text": "Open /dashboard", "status": "ok", "secs": 1.2, "shot": "step001.png"}\n'
        'not json\n{"n": 2, "text": "Click button \\"Save\\"", "status": "bad", "secs": 0.4, "shot": "", '
        '"error": "Timeout"}\n', encoding="utf-8")
    (tmp_path / "step001.png").write_bytes(b"png")
    job = {"dir": str(tmp_path)}
    steps = e2e.live_steps(job)
    assert [s["status"] for s in steps] == ["ok", "bad"] and steps[1]["error"] == "Timeout" and steps[1]["shot"] is None
    monkeypatch.setitem(e2e.JOBS, "j1", job)
    assert e2e.shot_file("j1", "step001.png").read_bytes() == b"png"
    for bad in ("../x.png", "run.webm", "steps.jsonl", "step1.png"):
        with pytest.raises(KeyError):
            e2e.shot_file("j1", bad)
