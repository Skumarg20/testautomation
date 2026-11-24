"""Feedback from the QA team: saved with where it came from, passwords cleaned out, a QA sees only their own, an admin
sees all and replies, and live feedback on a test shows as a known issue."""
from __future__ import annotations

import pytest

from ui_studio import accounts, feedback, mode, recorder, state
from tests.unit.test_studio_server_mode import _call, _client, srv  # noqa: F401  (fixture)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "DB", tmp_path / "studio.db")
    monkeypatch.setattr(state, "SETTINGS", tmp_path / "studio_settings.json")
    monkeypatch.setattr(recorder, "_secrets", lambda: ["TopSecret#1"])
    monkeypatch.setattr(feedback, "_env", lambda: "books6 · QA Chemist")
    accounts._fails.clear()
    yield


def test_add_keeps_the_context_and_never_the_password():
    r = feedback.add({"kind": "studio", "place": "run", "text": "Fails at step 6, password TopSecret#1 typed",
                      "test": "TC_COTH_173", "run": "R-0042", "step": "6", "error": "Not visible: x TopSecret#1",
                      "context": {"Module": "accounting", "bad": {"x": 1}}}, "qa1@qa.test", "QA One")
    assert r["ref"] == "FB-0001"
    item = feedback.list_feedback()["items"][0]
    assert item["test"] == "TC_COTH_173" and item["run"] == "R-0042" and item["step"] == "6"
    assert "TopSecret#1" not in str(item) and "***" in item["text"] and item["context"] == {"Module": "accounting"}
    assert item["status"] == "open" and item["by"] == "QA One" and item["env"] == "books6 · QA Chemist"


@pytest.mark.parametrize("bad", [{"kind": "nope", "text": "hello there"}, {"kind": "studio", "text": "hi"},
                                 {"kind": "studio", "text": "hello there", "context": "x"},
                                 {"kind": "studio", "text": ["a"]}])
def test_add_refuses_what_the_qa_must_fix(bad):
    with pytest.raises(feedback.FeedbackError):
        feedback.add(bad, "qa1@qa.test", "QA One")


def test_known_issues_follow_the_status_and_reply():
    a = feedback.add({"kind": "test_wrong", "place": "case", "text": "Expected result is old", "test": "TC_1"}, "qa1@qa.test")
    feedback.add({"kind": "idea", "text": "A dark theme please"}, "qa2@qa.test")
    assert feedback.known_issues()["TC_1"]["n"] == 1 and feedback.open_count() == 2
    row = feedback.update(a["id"], "fixed", "Expected result updated", "Boss")
    assert row["status"] == "fixed" and row["reply"] == "Expected result updated" and row["repliedBy"] == "Boss"
    assert "TC_1" not in feedback.known_issues() and feedback.open_count() == 1
    with pytest.raises(feedback.FeedbackError):
        feedback.update(a["id"], "done")
    with pytest.raises(KeyError):
        feedback.update(999, "fixed")


def test_list_filters_by_user_status_kind_and_text():
    feedback.add({"kind": "studio", "text": "Replay stuck on login", "test": "TC_9"}, "qa1@qa.test", "QA One")
    feedback.add({"kind": "app_bug", "text": "GST total wrong in GSTR-2"}, "qa2@qa.test", "QA Two")
    assert [i["by"] for i in feedback.list_feedback("qa1@qa.test")["items"]] == ["QA One"]
    assert len(feedback.list_feedback(kind="app_bug")["items"]) == 1
    assert len(feedback.list_feedback(q="GSTR")["items"]) == 1 and len(feedback.list_feedback(q="TC_9")["items"]) == 1
    assert len(feedback.list_feedback(status="live")["items"]) == 2
    assert feedback.list_feedback("qa1@qa.test")["counts"]["open"] == 1


def test_team_mode_qa_sees_own_admin_sees_all_and_replies(srv):  # noqa: F811
    base, _ = srv
    qa, boss = _client(), _client()
    assert _call(qa, base, "/api/auth/login", {"username": "qa1@qa.test", "password": "password123"})[0] == 200
    assert _call(boss, base, "/api/auth/login", {"username": "boss@qa.test", "password": "password123"})[0] == 200
    code, r, _ = _call(qa, base, "/api/feedback", {"kind": "studio", "place": "run", "text": "Run stopped at login",
                                                  "test": "TC_5", "who": "Someone Else"})
    assert code == 200 and r["ref"].startswith("FB-")
    _call(boss, base, "/api/feedback", {"kind": "idea", "text": "Admin note for later"})
    code, mine, _ = _call(qa, base, "/api/feedback?status=")
    assert code == 200 and not mine["admin"] and [i["by"] for i in mine["items"]] == ["QA One"]   # not the claimed name
    code, all_, _ = _call(boss, base, "/api/feedback?status=")
    assert all_["admin"] and len(all_["items"]) == 2
    assert _call(qa, base, "/api/feedback/update", {"id": str(r["id"]), "status": "fixed"})[0] == 403
    code, row, _ = _call(boss, base, "/api/feedback/update", {"id": str(r["id"]), "status": "in_progress",
                                                             "reply": "Looking at it"})
    assert code == 200 and row["repliedBy"] == "Boss"
    code, mine, _ = _call(qa, base, "/api/feedback?status=")
    assert mine["items"][0]["reply"] == "Looking at it"
    assert _call(qa, base, "/api/feedback/known")[1]["known"]["TC_5"]["n"] == 1
    assert _call(qa, base, "/api/feedback", {"kind": 5, "text": "x"})[0] == 400
    assert _call(boss, base, "/api/state")[1]["feedback_open"] == 1
    assert _call(qa, base, "/api/state")[1]["feedback_open"] == 0
    assert mode.SERVER
