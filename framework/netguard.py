"""
Network-level delete blocker -- ASLI pakka fix.

Ab tak ki saari suraksha "click mat hone do" wali thi. Us tareeke me ek buniyadi
khaami hai: agar delete kisi aur raste se chal jaye -- keyboard shortcut, app ka
apna JS, koi timer, ya browser ka koi event -- to click-guard kuch nahi kar sakta.

Yahan hum aakhri darwaze pe khade hain. Chahe delete kaise bhi trigger ho, uski
HTTP request server tak jayegi hi nahi. Isliye ye kaaran jaane bina bhi kaam
karta hai.

ALLOW_DESTRUCTIVE=true karne par ye hat jata hai (jaan-boojh kar).
"""
from __future__ import annotations

import re
import time

from config.settings import settings

# URL me ye ho -> likhne/mitane wali request
WRITE_PATH = re.compile(
    r"(delete|remove|destroy|erase|purge|/del/|/rm/|trash)", re.I)

# ---- Jaan-boojh kar ALLOW ki gayi calls ----
#
# Sab kuch andha-dhundh rokna bhi galat hai. TempBillHold/Delete MargBooks ka
# apna housekeeping hai: form band karte waqt wo BILL KA TEMPORARY DRAFT saaf
# karta hai -- wo draft humne hi khola tha, aur wo kisi ke asli data ka hissa
# nahi hai. Ise rokne se app me adhoore held-bill jama hote rehte hain.
#
# Yahan sirf wahi cheezein aayengi jinke baare me pakka pata ho ki wo
# session ka apna temporary data hai.
SAFE_PATHS = re.compile(r"(TempBillHold|TempHold|tempcart|/temp/|autosave)", re.I)
# ye HTTP method data badalte hain
WRITE_METHODS = {"DELETE"}

BLOCKED: list[dict] = []
ALLOWED_WRITES: list[dict] = []


def _is_delete(request) -> bool:
    """Ye request asli data mitane wali hai?"""
    if SAFE_PATHS.search(request.url):
        return False                      # session ka apna temp data -- rokna galat
    if request.method.upper() in WRITE_METHODS:
        return True
    if request.method.upper() in ("POST", "PUT", "PATCH") and WRITE_PATH.search(request.url):
        return True
    return False


def arm(context, verbose: bool = True) -> bool:
    """
    Context pe network guard lagao.
    True agar guard laga (ALLOW_DESTRUCTIVE=false), False agar jaan-boojh kar off hai.
    """
    if settings.ALLOW_DESTRUCTIVE:
        if verbose:
            print("  [netguard] ALLOW_DESTRUCTIVE=true -- delete requests JAANE DI JAYENGI")
        return False

    def handler(route, request):
        if _is_delete(request):
            BLOCKED.append({"t": round(time.time(), 2),
                            "method": request.method, "url": request.url[:200]})
            if verbose:
                print(f"  [netguard] BLOCKED {request.method} {request.url[:110]}")
            # 200 khali jawab -- app crash na ho, bas kuch delete na ho
            route.fulfill(status=200, content_type="application/json",
                          body='{"blocked_by":"mb-qa-netguard"}')
            return
        if SAFE_PATHS.search(request.url) and WRITE_PATH.search(request.url):
            ALLOWED_WRITES.append({"t": round(time.time(), 2),
                                   "method": request.method, "url": request.url[:200]})
        route.continue_()

    context.route("**/*", handler)
    return True


def report(path=None):
    """Kaunsi delete requests roki gayi -- file me likh do."""
    if not BLOCKED:
        return None
    path = path or (settings.ARTIFACTS / "blocked_requests.log")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["Ye delete/remove requests ROK DI GAYIN (ALLOW_DESTRUCTIVE=false):", ""]
    lines += [f"{b['t']}  {b['method']}  {b['url']}" for b in BLOCKED]
    if ALLOWED_WRITES:
        lines += ["", "Ye 'delete' dikhne wali calls JAAN-BOOJH KAR jaane di gayin",
                  "(session ka apna temporary data, kisi ka asli data nahi):", ""]
        lines += [f"{a['t']}  {a['method']}  {a['url']}" for a in ALLOWED_WRITES]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def count() -> int:
    return len(BLOCKED)
