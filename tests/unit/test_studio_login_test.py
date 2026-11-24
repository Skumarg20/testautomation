"""Login tests: a recording that checks the login screen keeps its login steps (the runner signs out first), and the
real MargBooks password never stays in the script, the saved YAML or the step log."""
import pytest

from ui_studio import recorder, script

REAL_USER, REAL_PW = "qa.user@example.com", "Real#Pass123"

CODE = """import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('https://books6.margbooks.com/login');
  await page.getByPlaceholder('Email address or mobile number').fill('%s');
  await page.getByRole('button', { name: 'SIGN IN' }).click();
  await page.getByRole('textbox').fill('%s');
  await page.getByRole('button', { name: 'CONTINUE' }).click();
  await expect(page.getByText('Please Enter The Valid Password')).toBeVisible();
});"""


@pytest.fixture(autouse=True)
def _known_login(monkeypatch):
    monkeypatch.setattr(recorder, "_secrets", lambda: [REAL_PW])
    monkeypatch.setattr(recorder, "_users", lambda: [REAL_USER])


def test_normal_recording_still_swaps_the_login_for_login_page():
    out = recorder.paste(CODE % (REAL_USER, "Wrong@1"), [])
    assert not out["login_test"] and "await login(page);" in out["code"] and "Wrong@1" not in out["code"]


def test_login_test_keeps_the_login_steps_and_a_wrong_password():
    out = recorder.paste(CODE % (REAL_USER, "Wrong@1"), [], True)
    code = out["code"]
    assert out["login_test"] and script.is_login_test(code)
    assert "login(page)" not in code and "fill('Wrong@1')" in code
    assert REAL_USER not in code and "fill(process.env.MB_USER!)" in code
    conv = script.to_steps(code)
    assert conv["unknown"] == [] and conv["login_test"]
    acts = [(s["action"], s.get("target"), s.get("value")) for s in conv["steps"]]
    assert acts[0][0] == "sign_out"                                  # starts signed out, on the login page
    assert ("fill", "login.password", "Wrong@1") in acts             # bare textbox on the login page = password
    assert ("fill", "placeholder=Email address or mobile number", "{{config_user}}") in acts
    assert not any(a == "goto" or (a == "open_screen") for a, _, _ in acts)   # the start page is not a step


def test_click_and_press_on_the_nameless_password_box_are_replayed():
    code = script.mark_login_test(CODE % ("x@y.in", "Wrong@1")).replace(
        "  await page.getByRole('textbox').fill('Wrong@1');",
        "  await page.getByRole('textbox').click();\n  await page.getByRole('textbox').fill('Wrong@1');\n"
        "  await page.getByRole('textbox').press('Enter');")
    conv = script.to_steps(code)
    assert conv["unknown"] == []
    acts = [(s["action"], s.get("target"), s.get("value")) for s in conv["steps"]]
    assert ("click", "login.password", None) in acts and ("press", "login.password", "Enter") in acts


def test_real_password_in_a_login_test_becomes_mb_pass_everywhere():
    out = recorder.paste(CODE % (REAL_USER, REAL_PW), [], True)
    assert REAL_PW not in out["code"] and "fill(process.env.MB_PASS!)" in out["code"]
    steps = script.to_steps(out["code"])["steps"]
    pw = [s for s in steps if s.get("target") == "login.password"][0]
    assert pw["value"] == "{{config_password}}" and REAL_PW not in str(steps)


def test_team_mode_qa_password_is_also_cleaned_in_a_login_test(monkeypatch):
    monkeypatch.setattr(recorder, "_secrets", lambda: [])
    out = recorder.paste(CODE % ("qa7@corp.in", "Qa7#Own99"), ["Qa7#Own99"], True, ["qa7@corp.in"])
    assert "Qa7#Own99" not in out["code"] and "qa7@corp.in" not in out["code"]
    assert "process.env.MB_PASS!" in out["code"] and "process.env.MB_USER!" in out["code"]


def test_mark_is_added_once_and_login_page_in_a_login_test_is_unknown():
    once = script.mark_login_test(script.mark_login_test(CODE % ("a", "b")))
    assert once.count("studio: login test") == 1
    bad = once.replace("  await page.goto('https://books6.margbooks.com/login');", "  await login(page);")
    conv = script.to_steps(bad)
    assert conv["unknown"] and "login test" in conv["unknown"][0]["why"]


def test_config_password_is_filled_only_at_run_time_and_never_shown(monkeypatch):
    from framework import data_factory
    from config.settings import settings
    monkeypatch.setattr(settings, "PASSWORD", REAL_PW)
    assert data_factory.resolve("config_password") == REAL_PW


def test_verify_flags_a_real_password_left_in_a_login_test():
    from ui_studio import verify
    code = script.mark_login_test(CODE % ("someone@x.in", REAL_PW))
    f = verify.r_login(code, {})
    assert f is not None and f.id == "login" and REAL_PW not in f.apply(code)
    assert verify.r_login(script.mark_login_test(CODE % ("someone@x.in", "Wrong@1")), {}) is None


def test_login_page_is_not_a_company_but_app_pages_still_are(monkeypatch):
    from framework import step_runner
    from config.settings import settings
    monkeypatch.setattr(settings, "LOGIN_URL", "https://books6.margbooks.com/login")

    class Pg:
        def __init__(self, url):
            self.url = url

        def inner_text(self, *_a, **_k):
            return ""

    class P:
        def __init__(self, url):
            self.page = Pg(url)

    assert step_runner._before_company(P("https://margbooks.com/login/"), "fill")
    assert step_runner._before_company(P("https://books6.margbooks.com/login?c=x"), "click")
    assert not step_runner._before_company(P("https://margbooks.com/login/"), "save_form")
    assert not step_runner._before_company(P("https://books6.margbooks.com/sale/bill"), "fill")
    assert not step_runner._before_company(P("https://evil.example/margbooks.com/login/"), "fill")


def test_if_text_and_unless_text_decide_whether_a_step_runs():
    from framework.step_runner import StepRunner, RunContext
    ran = []

    class Loc:
        def __init__(self, ok):
            self.first = self
            self.ok = ok

        def is_visible(self, timeout=None):
            return self.ok

    class Page:
        def get_by_text(self, t, exact=False):
            return Loc(t == "Bill Adjustment")

    class P:
        page = Page()

    r = StepRunner.__new__(StepRunner)
    r.p, r.ctx = P(), RunContext()
    r._dispatch_once = lambda a, t, v, s: ran.append(s["n"])
    r._dispatch("press", None, "F10", {"n": 1, "if_text": "Bill Adjustment"})       # popup there: runs
    r._dispatch("press", None, "F10", {"n": 2, "if_text": "Something else"})        # not there: skipped
    r._dispatch("press", None, "F10", {"n": 3, "unless_text": "Bill Adjustment"})   # already there: skipped
    r._dispatch("press", None, "F10", {"n": 4, "unless_text": "Select Party"})      # not there: runs
    assert ran == [1, 4]
