"""
Why a test failed, in simple words a manual QA understands: what happened, the likely reason, what to do next and
whose side it is on (the test, the app, the test data / setup, or the login / Studio).

Local rules first (free, instant), written from the failures this project really meets. They read the error text
and the step; nothing is guessed: an error no rule knows gets a plain generic summary, and the "Explain in simple
words" button can ask AI (explain_ai) for that one case.
"""
from __future__ import annotations

import re

SIDES = {"test": "Problem in the test (its steps or expected values need a change)",
         "app": "Possible problem in MargBooks (check it by hand and report it)",
         "setup": "Problem with the test data or the company setup, not the app",
         "login": "Problem with the login or the environment",
         "studio": "Problem in Test Studio itself (report it with the Feedback button)",
         "none": ""}


def _q(m: re.Match | None, i: int = 1) -> str:
    return (m.group(i) if m else "").strip()


def _readable_target(t: str) -> str:
    """xpath=//div[...="19,960.00 Cr"][...QA_Supplier_Reg...] -> "19,960.00 Cr" (QA_Supplier_Reg); #btnSave -> Save."""
    quoted = re.findall(r'=\s*\\?"([^"\\]{2,60})\\?"', t)
    words = [w for w in quoted if not re.fullmatch(r"[\w-]+", w) or re.search(r"[A-Z]", w)]
    if words:
        return ", ".join(f"“{w}”" for w in words[:3])
    m = re.search(r"role=(\w+):(.+)$|name=[\"']([^\"']+)", t)
    if m:
        return f"“{(m.group(2) or m.group(3) or '').strip()}”"
    m = re.search(r"#(?:btn|txt|ddl|chk)?([A-Za-z]+)", t)
    if m:
        return f"the “{re.sub(r'(?<!^)(?=[A-Z])', ' ', m.group(1))}” box/button"
    return f"“{t[:60]}”" if t else "it"


def _numbers(text: str) -> list[str]:
    return re.findall(r"\d[\d,]*\.\d{2}\s*(?:Cr|Dr)?", text or "")


def explain(err: str, step_text: str = "", result: str = "") -> dict:
    """{"what", "why", "next", "side", "side_text"} for a failed / blocked / skipped test (empty for a pass)."""
    e, step = err or "", (step_text or "").strip()
    stepn = _q(re.search(r"Step (\d+)", e))
    at = f"Step {stepn}" if stepn else "A step"
    lo = e.lower()

    def out(what, why, nxt, side):
        return {"what": what, "why": why, "next": nxt, "side": side, "side_text": SIDES[side]}

    if not e and result in ("", "Pass", "passed"):
        return {}
    if result in ("Skip", "skipped") or lo.startswith("not run"):
        if "create or change data" in lo:
            return out("The test was not run, because it saves data and saving is switched off.",
                       "Settings > App under test > “Allow tests that create or change data” is off.",
                       "Turn it on if this test may save data in the QA test company, then run it again.", "setup")
        if "precondition" in lo or "4426" in lo:
            return out("The test was not run: the company does not have what this test needs.",
                       _q(re.search(r"precondition:?\s*(.+)", e, re.I | re.S))[:220] or e[:220],
                       "Run it in a company that has this setting, or ask the admin to set it up.", "setup")
        return out("The test was not run (skipped).", e[:220] or "The test said it does not apply here.",
                   "Read the reason; usually the company or a setting is not right for this test.", "setup")

    if "[studio-guard] blocked" in lo or "not a qa test company" in lo or "refused to run" in lo:
        return out(f"{at} was stopped before it could save anything.",
                   "The test tried to save or change data in a company that is not a QA test company. Real "
                   "companies are read-only for tests, so nothing was written.",
                   "Make the test open a QA test company first (for example QA Chemist), then run it again.", "test")
    if "rok diya gaya (suraksha)" in lo or "unsafeclick" in lo:
        return out(f"{at} was stopped by the safety check.",
                   "The step would click something dangerous (for example Delete) that the test is not allowed to.",
                   "Check the step: it should not delete real data. Change the step if it is wrong.", "test")
    if re.search(r"registered mobile no|waiting for locator\(\"input#password\"\)|could not sign in|signinfailed|"
                 r"sign-in try|login(?:blocked)?\b.*fail", lo):
        return out("The test could not log in to MargBooks.",
                   "The MargBooks user id or password in Settings is wrong, or the login page changed.",
                   "Press Settings > Test login. Fix the login there and run again.", "login")
    if re.search(r"net::err_|err_name_not_resolved|err_connection|err_internet", lo):
        return out("The browser could not reach MargBooks.",
                   "The internet / VPN was down or MargBooks did not answer.",
                   "Check the network and open MargBooks in your own browser, then run again.", "login")
    if re.search(r"target page, context or browser has been closed|browser has been closed|session ended", lo):
        return out(f"{at} could not finish: the browser page closed in the middle.",
                   "MargBooks logged the test out (the same login was used somewhere else at the same time) or the "
                   "browser was closed.",
                   "Do not use the same MargBooks login elsewhere during a run. Run the test again.", "login")
    if "stock" in lo and ("not enough" in lo or "negative" in lo):
        return out(f"{at} failed: the item did not have enough stock.",
                   "Other tests sold this item's stock before this test ran.",
                   "Add stock to the item in the QA company (or let Studio put test data back) and run again.", "setup")
    if "is not in this company any more" in lo or "test data" in lo and "used" in lo:
        return out(f"{at} failed: the test data it needs is missing.",
                   "Another test used or deleted the party / item / bill this test needs.",
                   "Create the missing data in the QA company again, then run the test again.", "setup")
    if re.search(r"settinglocked|featureoff|module.*not enabled|control room|precondition", lo):
        return out(f"{at} failed because of a company setting.",
                   "A Control Room setting this test needs is not set (or may not be changed by tests).",
                   "Ask the admin to set the setting named above in the QA company, then run again.", "setup")
    if re.search(r"disabled|not enabled|readonly", lo):
        return out(f"{at} failed: the box or button was greyed out (disabled).",
                   "A Control Room setting decides whether this field can be used, and it is off in this company.",
                   "Turn the setting on in the QA company (or use a company where it is on) and run again.", "setup")
    if re.search(r"intercepts pointer|covered by", lo):
        return out(f"{at} failed: a popup window was covering the screen.",
                   "A window (for example a batch, discount or confirmation popup) opened and was not closed by the "
                   "test.",
                   "Add a step that answers / closes that popup before this step.", "test")
    if "strict mode violation" in lo:
        return out(f"{at} failed: more than one thing on the screen matched.",
                   "The step points at a button / box that appears more than once, so the test cannot tell which.",
                   "Make the step more exact (name the screen or the row).", "test")

    m = re.search(r"expected to have (?:text|value) ['\"]?(.+?)['\"]?\s*\n?\s*Actual value:\s*(.+?)(?:\n|$)", e, re.S)
    if m:
        want, got = _q(m, 1)[:80], _q(m, 2)[:80]
        return out(f"{at} failed: MargBooks showed “{got}”, the test expected “{want}”.",
                   "Either the app shows a different value than it should, or the test expects an old / fixed value "
                   "(numbers like totals and balances change every time other tests run).",
                   "Check the value by hand in MargBooks. If the app is right, change the expected value in the test; "
                   "if the app is wrong, report it as an app bug.", "app")
    m = re.search(r"Not the same:\s*'?(.+?)'?\s+vs\s+'?(.+?)'?(?:\n|$)", e)
    if m:
        return out(f"{at} failed: two figures that should match did not ({_q(m, 1)[:50]} and {_q(m, 2)[:50]}).",
                   "The amount changed by a different value than the test expects.",
                   "Check both figures by hand. A real difference is an app bug; else fix the expected change.",
                   "app")
    m = re.search(r"Page URL expected to be .*?\n?\s*Actual value:\s*(\S+)", e, re.S)
    if m:
        url = _q(m)
        where = "the login page" if "/login" in url else "the company list" if "user-company" in url else url
        return out(f"{at} failed: the expected screen did not open; MargBooks stayed on {where}.",
                   "The previous step did not finish (for example the login or company choice did not go through).",
                   "Open the screenshot of the failing step to see where it stopped.", "login" if "/login" in url else "test")
    m = re.search(r"Not visible:\s*(.+)", e)
    if m or "no visible text" in lo:
        target = _readable_target(_q(m)) if m else \
            f"“{_q(re.search(r'no visible text ([^\n]+?) after', e)).strip(chr(39) + chr(34))}”"
        nums = _numbers(target)
        if nums:
            return out(f"{at} failed: the screen did not show {', '.join(nums)}.",
                       "The test expects a fixed amount, but amounts like balances and totals change every time a "
                       "bill is saved (by this test or others).",
                       "Change the test to read the amount before and after, and check the difference instead.", "test")
        return out(f"{at} failed: the screen did not show {target}.",
                   "The screen was different from what the test expects: it opened late, a popup was in the way, "
                   "or the label / data is different in this company.",
                   "Look at the screenshot of this step. If the screen is right, change the step; if MargBooks is "
                   "wrong, report it.", "test")
    if re.search(r"timeout|waiting for|not found|nahi mila", lo):
        target = _readable_target(_q(re.search(r"waiting for (?:locator\()?['\"]?([^\n'\")]+)", e)))
        return out(f"{at} failed: {target} was not found on the screen in time.",
                   "The screen was slow, a popup was in the way, or the button / box has a different name now.",
                   "Look at the screenshot of this step. If the screen looks right, the step must be updated.",
                   "test")
    first = next((ln.strip() for ln in e.split("\n") if ln.strip()), "")
    return out(f"{at} failed." + (f" ({step[:80]})" if step else ""),
               f"The message from the test was: {first[:200]}" if first else "No message was given.",
               "Open the screenshot and the video of the run. Use “Explain in simple words” for an AI explanation.",
               "test")


def explain_ai(err: str, step_text: str = "", test_name: str = "") -> dict:
    """AI explanation for an error the rules do not know. Cached and metered like every Studio AI call."""
    from ui_studio import state
    ans, _tok, _cached = state.ai_json(
        "explain.failure",
        "You explain an automated UI test failure of MargBooks (an accounting web app) to a manual QA who does not "
        "read code. Simple English, short sentences, no code, no selectors. Reply JSON {\"what\": \"what happened, "
        "one sentence\", \"why\": \"the most likely reason\", \"next\": \"what the QA should do next\", \"side\": "
        "\"test|app|setup|login\"}.",
        f"test: {test_name[:120]}\nstep: {step_text[:200]}\nerror: {err[:1200]}", 400)
    side = str((ans or {}).get("side") or "test")
    side = side if side in SIDES else "test"
    return {"what": str(ans.get("what") or ""), "why": str(ans.get("why") or ""), "next": str(ans.get("next") or ""),
            "side": side, "side_text": SIDES[side], "ai": True}
