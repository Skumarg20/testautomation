"""Test Studio QA guard: in Test Studio mode, real companies stay read-only, at the network level.

Every MargBooks API request carries the open company in its `complinkid` header. A request that saves, changes or
deletes data (found by its method and the verb in its path) goes out only when that company is one of the QA test
companies; any other is aborted before it reaches the server, and the test fails with the reason. Control Room
setting saves are refused everywhere: settings are changed by Test Studio steps, which refuse one-way settings.

Inactive (no route at all) unless Test Studio set STUDIO_QA_GUARD=1.
"""

import base64
import re
from typing import Any

from playwright.sync_api import BrowserContext, Request, Route

from config.settings import STUDIO_QA_COMPLINKIDS, STUDIO_QA_GUARD

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# The verb that STARTS the last part of the path says whether a POST writes (gRPC-web and REST both POST their
# reads): CallGrpcSaveSaleBill, UpdateItem, DeleteLedger write; GetList, NEWLYADDEDASHBOARD read.
WRITE_VERB = re.compile(
    r"^(?:call)?(?:grpc)?_?(save|insert|update|delete|remove|add|create|modify|cancel|post|import|upload|merge|"
    r"restore|rebuild|approve|reject|lock|unlock|submit|transfer|convert|adjust|reset|clear|purge|destroy|assign|"
    r"change|set(?!ting)|generateeinvoice|generateewaybill|bulk|sync)",
    re.I,
)
SETTING_SAVE = re.compile(r"(controlroom|profiler|userpower|usersetting|configuration|/settings?/)"
                          r".*(save|update|set|insert)|(save|update|set|insert)\w*(controlroom|profiler|userpower)",
                          re.I)
# The app's own scratch data while a screen is open (a held draft), and what the app itself sends while signing in
# (last-used company and user), never a record of the company.
SCRATCH = re.compile(r"(TempBillHold|TempHold|tempcart|/temp/|autosave|log(?:ger)?/|telemetry|analytics|"
                     r"Company/UpdateCompanyProfileAndUser)", re.I)

BLOCKED: list[str] = []


def is_write(method: str, url: str) -> bool:
    if method.upper() not in WRITE_METHODS:
        return False
    path = url.split("?", 1)[0]
    if SCRATCH.search(path):
        return False
    if method.upper() in ("PUT", "PATCH", "DELETE"):
        return True
    last = path.rstrip("/").rsplit("/", 1)[-1]
    return bool(WRITE_VERB.search(last))


def company_id(header: str) -> str:
    """The company id of a complinkid header: plain digits (gRPC-web) or base64 of the digits (REST v4.2)."""
    value = header.strip()
    if value.isdigit():
        return value
    try:
        decoded = base64.b64decode(value, validate=True).decode("ascii").strip()
    except (ValueError, UnicodeDecodeError):
        return value
    return decoded if decoded.isdigit() else value


def refusal(method: str, url: str, headers: dict[str, str]) -> str:
    """Why this request must not go out ('' = it may)."""
    if not is_write(method, url):
        return ""
    path = url.split("?", 1)[0].split("://", 1)[-1].split("/", 1)[-1]        # without scheme and host
    if SETTING_SAVE.search(path):
        return "a Control Room / settings save (Test Studio changes settings only through its own steps)"
    company = company_id(headers.get("complinkid") or "")
    if company and company in STUDIO_QA_COMPLINKIDS:
        return ""
    if not company or company == "0":
        return ""                                   # no company yet (login, company list): not company data
    return f"a write in company {company}, which is not a QA test company"


def arm(context: BrowserContext) -> None:
    if not STUDIO_QA_GUARD:
        return
    context.route("**/*", _check)


def _check(route: Route, request: Request) -> None:
    why = refusal(request.method, request.url, _headers(request))
    if not why:
        route.fallback()
        return
    BLOCKED.append(f"{request.method} {request.url.split('?', 1)[0]}: {why}")
    print(f"[studio-guard] BLOCKED {BLOCKED[-1]}", flush=True)
    route.abort("blockedbyclient")


def _headers(request: Request) -> dict[str, Any]:
    return {k.lower(): v for k, v in request.headers.items()}
