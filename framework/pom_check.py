"""
POM ka imtihan -- SIRF PADHNE WALE kaam. Kuch save nahi hota.

    python -m framework.pom_check     (ya pom-check.bat)
"""
from playwright.sync_api import sync_playwright

from config.settings import settings
from framework import safety, netguard, event_recorder
from framework.browser import launch, describe_window
from framework.auth import login
from framework.screens_check import ensure_neutral
from pages import ItemPage, PartyPage, SaleBillPage

results: list[tuple[str, bool, str]] = []


def check(name, fn, expect=None):
    """
    expect: ek function jo natije ko dekh kar True/False de.
    Diya hai to natija GALAT hone par FAIL hoga -- sirf 'crash nahi hua' se
    OK nahi milega. Pichhli baar isi wajah se search ka test jhootha pass
    ho gaya tha (61 rows aa rahe the, 0 aane chahiye the).
    """
    try:
        detail = fn()
        if expect is not None and not expect(detail):
            results.append((name, False, f"natija galat: {detail!r}"))
            print(f"  FAIL  {name}\n        natija galat: {str(detail)[:110]}")
            return
        results.append((name, True, str(detail)[:110]))
        print(f"  OK    {name}  {str(detail)[:80]}")
    except Exception as e:  # noqa: BLE001
        results.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"  FAIL  {name}\n        {type(e).__name__}: {str(e)[:150]}")


def main():
    settings.validate()
    run = settings.init_run("POM check (read-only)")

    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        bp = login(ctx.new_page(), verbose=True)
        print(f"\nWindow: {describe_window(bp.page)}")

        # ---------- Item ----------
        print("\n--- ItemPage ---")
        item = {}
        check("item.open", lambda: item.setdefault("p", ItemPage.open(bp)) and "khul gaya")
        if "p" in item:
            p = item["p"]
            base = {}
            # virtual scroll: DOM me sirf dikhne wali rows hoti hain, isliye
            # ginti ke liye header ka TOTAL label use karte hain.
            check("item.total (label padha ja raha hai)",
                  lambda: base.setdefault("t", p.total()),
                  expect=lambda n: isinstance(n, int))
            check("item.rows == total (0 ho to Item List khali hai)",
                  lambda: (len(p.rows()), base.get("t")),
                  expect=lambda v: v[0] >= 1 or v[1] == 0)
            # Filter ka sahi paimana: dikh rahi HAR row me shabd ho.
            # (Header ka total filter pe badalta hi nahi -- wo DB ka total hai.)
            if base.get("t"):
                check("item.search('Sample') -> kaam kare",
                      lambda: p.search_check("Sample"),
                      expect=lambda r: r["works"])
            # Bakwaas search par app ko KUCH kehna chahiye -- ya "not found"
            # alert, ya list khali. Chupchaap kuch na karna hi bug hai.
            check("item.search(bakwaas) -> list khali ya 'not found'",
                  lambda: p.search_check("ZZQQ_NOPE_999"),
                  expect=lambda r: r["mode"] in ("not_found", "filter_empty"))
            check("item.clear_search -> list wapas normal",
                  lambda: p.clear_search().names()[:1],
                  expect=lambda v: bool(v))
            check("item.details", lambda: p.item_details())
            bp.screenshot("pom_item")

        # ---------- Party ----------
        print("\n--- PartyPage ---")
        ensure_neutral(bp)
        party = {}
        check("party.open", lambda: party.setdefault("p", PartyPage.open(bp)) and "khul gaya")
        if "p" in party:
            p = party["p"]
            pbase = {}
            check("party.total (label se)", lambda: pbase.setdefault("t", p.total()),
                  expect=lambda n: isinstance(n, int) and n > 1)
            check("party.rows dikh rahi hain", lambda: len(p.rows()),
                  expect=lambda n: n >= 1)
            # Ledger ka search FILTER nahi karta -- matching record ko upar
            # le aata hai (jump). Item ka search filter karta hai. Ek hi app
            # me do alag vyavhaar -- test dono jhel leta hai.
            check("party.search('Cash') -> kaam kar raha hai",
                  lambda: p.search_check("Cash"),
                  expect=lambda r: r["works"])
            check("party.search(bakwaas) -> list khali ya 'not found'",
                  lambda: p.search_check("ZZQQ_NOPE_999"),
                  expect=lambda r: r["mode"] in ("not_found", "filter_empty"))
            check("party.has('Cash Account')", lambda: p.has("Cash Account"),
                  expect=lambda v: v is True)
            check("party.clear_search -> list wapas normal",
                  lambda: p.clear_search().names()[:1],
                  expect=lambda v: bool(v))
            check("party.all_rows (scroll karke saari)",
                  lambda: len(p.all_rows()),
                  expect=lambda n: n > 5)
            bp.screenshot("pom_party")

        # ---------- Sale Bill (padhna hi padhna) ----------
        print("\n--- SaleBillPage (read-only, save NAHI) ---")
        ensure_neutral(bp)
        sale = {}
        check("sale.open", lambda: sale.setdefault("p", SaleBillPage.open(bp, verbose=True))
              and "khul gaya")
        if "p" in sale:
            p = sale["p"]
            check("sale.suffix (dynamic id)", lambda: f"suffix = {p.suffix}")
            check("sale.get_bill_no", lambda: p.get_bill_no(),
                  expect=lambda v: bool(str(v).strip()))
            check("sale.get_date", lambda: p.get_date(),
                  expect=lambda v: "-" in str(v))
            check("sale.get_party", lambda: repr(p.get_party()))
            check("sale.get_totals", lambda: p.get_totals())
            check("sale.line_count (khali bill = 0)", lambda: p.line_count(),
                  expect=lambda n: isinstance(n, int))
            bp.screenshot("pom_sale_bill")
            check("sale.close (bina save)", lambda: p.close() and "band")

        # kya kya toast aaye? (delete/error chupke se hua to yahan dikhega)
        toasts = safety.get_toasts(bp.page)
        clicks = safety.flush_click_log()
        ensure_neutral(bp)
        # suraksha ki report -- kya kuch roka gaya
        ev_path = event_recorder.report(bp.page, settings.ARTIFACTS / "events.log")
        del_path = safety.delete_report(bp.page, settings.ARTIFACTS / "delete_attempts.log")
        n_del = safety.delete_count(bp.page)
        if n_del:
            print(f"\n  !! DELETE confirmation {n_del} baar aayi -- har baar 'No' dabaya")
            print(f"     Kyun aayi, ye dekho: {del_path}")
        ng_path = netguard.report()
        if netguard.count():
            print(f"\n  !! {netguard.count()} DELETE request ROKI GAYIN -> {ng_path}")
        browser.close()

    ok = sum(1 for _, g, _ in results if g)
    lines = [f"POM CHECK -- {settings.RUN_ID}",
             f"{ok}/{len(results)} pass", ""]
    if toasts:
        lines += ["APP TOASTS (jo bhi message screen pe aaya):"]
        lines += [f"  {t['t']}" for t in toasts] + [""]
        print("\n--- App toasts ---")
        for t in toasts:
            print(f"  {t['t']}")
    if clicks:
        lines += [f"Click log: {clicks}", ""]
    for n, g, d in results:
        lines.append(f"{'OK  ' if g else 'FAIL'}  {n}\n        {d}")
    (run / "pom_result.txt").write_text("\n".join(lines), encoding="utf-8")

    print(f"\n{'='*58}")
    print(f"  {ok}/{len(results)} pass")
    print(f"  {run / 'pom_result.txt'}")
    print(f"{'='*58}")


if __name__ == "__main__":
    main()
