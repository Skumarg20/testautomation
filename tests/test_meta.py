"""Suite khud healthy hai ya nahi -- browser ke bina chalta hai."""
from framework.case_loader import load_all
from framework.locator_store import store


def test_all_cases_parse():
    cases = load_all()
    assert cases, "testcases/ folder khali hai"


def test_every_target_has_a_locator():
    """Har YAML step ka target locators file me hona chahiye. Ye CI me
    tab fail hoga jab koi naya case likhe par locator map na kare."""
    missing = set()
    known = set(store.all_keys())
    for c in load_all():
        for s in c.steps:
            t = s.get("target")
            if t and not t.startswith("/") and "." in t and t not in known:
                missing.add(f"{c.id}: {t}")
    assert not missing, "Locators file me ye keys missing hain:\n" + "\n".join(sorted(missing))


def test_ids_follow_convention():
    for c in load_all():
        assert c.id.startswith("TC_"), f"{c.id} should start with TC_"
        assert c.priority in ("p1", "p2", "p3"), f"{c.id} bad priority"
