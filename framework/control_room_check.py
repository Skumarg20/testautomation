"""
Control Room ki settings padho aur yaad rakh lo.

    python -m framework.control_room_check      (ya control-room.bat)

Ek baar chala do. Uske baad har test ko pata rehta hai ki kaunsa feature
is company me chaalu hai aur kaunsa band -- aur band wale test FAIL nahi,
SKIP hote hain.
"""
from playwright.sync_api import sync_playwright

from config.settings import settings
from framework import control_room
from framework.auth import login
from framework.browser import launch


def main():
    settings.validate()
    run = settings.init_run("control room read")
    print("\n=== CONTROL ROOM ===\n")

    with sync_playwright() as pw:
        browser, ctx = launch(pw)
        bp = login(ctx.new_page(), verbose=True)
        try:
            data = control_room.capture(bp, verbose=True)
        except control_room.ControlRoomNotOpen as e:
            print(f"\n  !! {e}")
            bp.screenshot("control_room_fail")
            browser.close()
            print(f"\n  Screenshot: {run}")
            return
        browser.close()

    print(f"\n  {data['total']} settings padhi gayin\n")
    print("  Jo humare tests par asar daalti hain:")
    for k, v in data["settings"].items():
        state = "ON " if v["on"] is True else "OFF" if v["on"] is False else "?  "
        print(f"    [{state}] {k:<26} {v['label']} = {v['value']}")
    if not data["settings"]:
        print("    (koi pehchani hui setting nahi mili -- "
              "control_room.txt me poori list dekho)")

    path = control_room.report(run / "control_room.txt")
    print(f"\n  Poori list: {path}")
    print(f"  Yaad rakh li gayi: config/control_room.json\n")


if __name__ == "__main__":
    main()
