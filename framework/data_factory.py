"""Deterministic-ish fake data. Sab kuch DATA_PREFIX se start hota hai
taki demo account me humara banaya data pehchana aur clean kiya ja sake."""
from __future__ import annotations

import random
import time
from faker import Faker

from config.settings import settings

fake = Faker("en_IN")
P = settings.DATA_PREFIX


def _stamp() -> str:
    return f"{int(time.time() * 1000) % 10_000_000}"


def today() -> str:
    """Today in the app's date format (dd-mm-yyyy). Test Studio's `{{today}}`, from today() in a script."""
    return time.strftime("%d-%m-%Y")


def item_name() -> str:
    return f"{P}ITEM_{_stamp()}"


def party_name() -> str:
    return f"{P}{fake.company().replace(',', '')[:20]}_{_stamp()}"


def batch_no() -> str:
    return f"{P}B{random.randint(1000, 9999)}"


def hsn() -> str:
    return random.choice(["3004", "3003", "2106", "8471", "9018"])


def gstin(state_code: str = "07") -> str:
    """Structurally valid-looking GSTIN (checksum not computed -- negative tests ke liye
    `valid=False` wala variant use karo)."""
    pan = f"{fake.lexify('?????').upper()}{fake.numerify('####')}{fake.lexify('?').upper()}"
    return f"{state_code}{pan}1Z5"


def invalid_gstin() -> str:
    return "07ABCDE1234F1Z"  # ek digit kam -> validation fire honi chahiye


def mobile() -> str:
    return f"9{fake.numerify('#########')}"


def qty() -> int:
    return random.randint(1, 20)


def rate() -> float:
    return round(random.uniform(10, 2000), 2)


def gst_rate() -> int:
    return random.choice([0, 5, 12, 18, 28])


def unregistered_user() -> str:
    """
    Aisa login id jo KABHI register nahi ho sakta.

    ".invalid" TLD internet ke niyam (RFC 2606) se hamesha ke liye rakha gaya
    hai -- uspe koi domain le hi nahi sakta, isliye uspe account ban hi nahi
    sakta.

    Pehle main 9999999999 use kar raha tha. Wo random laga tha, par uspe asli
    account nikla -- aur test galat raaste chala gaya. Koi bhi "random dikhne
    wala" number kisi ka asli account ho sakta hai. Andaza nahi lagana chahiye
    jab pakka tareeka maujood ho.
    """
    return f"qa.no.account.{int(time.time()) % 100000}@margbooks-qa.invalid"


def config_user() -> str:
    """.env me set kiya hua ASLI user -- galat password wale test ke liye."""
    from config.settings import settings
    return settings.USER


def config_password() -> str:
    """The runner's own MargBooks password (a login test types it). Never written in a test: the test holds
    {{config_password}} and this fills it in only when the step runs."""
    from config.settings import settings
    return settings.PASSWORD


def resolve(token: str):
    """YAML me `{{item_name}}` jaise placeholders resolve karta hai."""
    mapping = {
        "config_password": config_password,
        "item_name": item_name, "party_name": party_name, "batch_no": batch_no,
        "hsn": hsn, "gstin": gstin, "invalid_gstin": invalid_gstin,
        "mobile": mobile, "qty": qty, "rate": rate, "gst_rate": gst_rate,
        "unregistered_user": unregistered_user, "config_user": config_user, "today": today,
    }
    fn = mapping.get(token)
    return fn() if fn else None
