"""
Exploratory testing agent (bounded, read-only by default).

Claude ko browser ka control deta hai: wo screen dekhta hai, decide karta hai
next click/fill kya ho, aur jo bhi anomaly mile (console error, broken layout,
wrong total, dead link, missing validation) usko note karta hai.
Har run ke end me findings + suggested new test cases aate hain.

    python -m agent.explore --start /sale/invoice --steps 25
    python -m agent.explore --start /masters/item --steps 40 --allow-writes
"""
from __future__ import annotations

import argparse
import json
from playwright.sync_api import sync_playwright
from rich import print as rprint

from config.settings import settings
from framework import safety
from framework.browser import launch
from agent.client import ask_json, condense_dom
from framework.base_page import BasePage
from framework.auth import login

SYSTEM = """You are an exploratory tester driving a real browser on MargBooks
(Marg ERP cloud accounting/billing/inventory, Indian GST domain).

Each turn you get the condensed DOM, recent console errors, and your own history.
Decide ONE next action and report anything suspicious you can already see.

Output JSON:
{"observation": "what you see now, 1-2 sentences",
 "findings": [{"severity":"high|medium|low","area":"...","issue":"...",
               "why_it_matters":"...","repro":"short steps"}],
 "next": {"action":"click|fill|select|goto|press|stop",
          "selector":"a raw Playwright selector for THIS page",
          "value":"...", "rationale":"why this probes something risky"}}

Guidance:
- Hunt for real defects: wrong GST split, totals that don't add up, rounding drift,
  validation that never fires, values lost on re-render, stale data after save,
  dead controls, unhandled errors.
- Prefer probing edge inputs (0, negative, very large, special chars, past/future
  dates) over happy-path clicking.
- WRITE_MODE tells you whether you may submit/save. If it is false, never click
  save/submit/delete/post -- fill fields and inspect computed values instead.
- Emit "stop" when the area is well covered or you're stuck in a loop."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="/")
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--allow-writes", action="store_true")
    args = ap.parse_args()

    write_mode = args.allow_writes and settings.ALLOW_DESTRUCTIVE
    if args.allow_writes and not settings.ALLOW_DESTRUCTIVE:
        rprint("[yellow]ALLOW_DESTRUCTIVE=false hai -- read-only mode me chal raha hoon.[/]")

    settings.validate()
    history, findings = [], []

    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        page = ctx.new_page()
        console_errors: list[str] = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))

        bp = login(page)
        bp.goto(args.start)

        for i in range(1, args.steps + 1):
            page.wait_for_timeout(600)
            try:
                turn = ask_json(
                    SYSTEM,
                    f"WRITE_MODE={write_mode}\nStep {i}/{args.steps}\n"
                    f"History:\n{json.dumps(history[-10:], indent=1)}\n"
                    f"Console errors since last turn: {console_errors[-8:]}\n"
                    f"DOM:\n{condense_dom(page)}",
                    max_tokens=2500,
                )
            except Exception as e:  # noqa: BLE001
                rprint(f"[red]agent error: {e}[/]")
                break
            console_errors.clear()

            for f in turn.get("findings", []):
                findings.append({**f, "step": i, "url": page.url})
                sev = {"high": "red", "medium": "yellow"}.get(f["severity"], "white")
                rprint(f"  [{sev}]FINDING[/] [{f['severity']}] {f['area']}: {f['issue']}")

            nxt = turn.get("next", {})
            act = nxt.get("action")
            rprint(f"[dim]{i:>3}[/] {turn.get('observation','')[:100]} -> {act} {nxt.get('selector','')}")
            if act == "stop":
                break
            try:
                sel, val = nxt.get("selector"), nxt.get("value")
                if act == "goto":
                    bp.goto(sel or val or "/")
                elif act == "click":
                    # AI khud selector chunta hai -- isliye guard yahan SABSE
                    # zyada zaroori hai. UnsafeClick uthega to wo history me
                    # chala jayega aur agent agla kadam sochega.
                    safety.guarded_click(page.locator(sel).first,
                                         f"ai:{sel[:40]}", timeout=6000)
                elif act == "fill":
                    page.locator(sel).first.fill(str(val), timeout=6000)
                elif act == "select":
                    page.locator(sel).first.select_option(label=str(val), timeout=6000)
                elif act == "press":
                    page.locator(sel).first.press(str(val), timeout=6000)
                history.append({"step": i, "action": act, "selector": sel, "value": val, "ok": True})
            except Exception as e:  # noqa: BLE001
                history.append({"step": i, "action": act, "selector": nxt.get("selector"),
                                "ok": False, "error": str(e)[:200]})

        browser.close()

    out = settings.ARTIFACTS / "exploration.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"findings": findings, "history": history}, indent=2))
    highs = [f for f in findings if f["severity"] == "high"]
    rprint(f"\n[bold]{len(findings)} findings ({len(highs)} high) -> {out}[/]")
    rprint("[dim]Ab `python -m agent.generate` se in findings ko permanent test cases bana lo.[/]")


if __name__ == "__main__":
    main()
