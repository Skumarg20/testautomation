"""Test-owned units and HSN/SAC codes for J26 (specs/unit-uqc-hsn-rate-masters.md).

The unit name field holds 10 characters and the HSN code field 8, so these names cannot follow the usual
`QA-<run_id>-...` pattern in full: units are `QA` + 7 run-id characters + one base-36 serial character (36
units per factory), HSN codes are digits derived from the run id plus one serial digit (10 codes per factory).
HSN names keep the full pattern. Asking for more raises instead of returning a duplicate the app would refuse.
"""

import string
from dataclasses import dataclass
from itertools import count

# UQC options seen in the Create Unit list on the garments QA company, 2026-10-09.
BOX_UQC = "BOX-BOX"
PIECES_UQC = "PCS-PIECES"
# A predefined unit of the QA company; the app refuses to delete it before asking to confirm.
PREDEFINED_UNIT = "TUBE"
UNIT_NAME_LENGTH = 10
HSN_CODE_LENGTH = 8
HEX_BASE = 16
# The leading digit keeps generated codes clear of the 12345678 / 54545454 codes other suites use.
HSN_LEADING_DIGIT = "9"
HSN_SERIAL_DIGITS = 1
UNIT_RUN_ID_CHARS = UNIT_NAME_LENGTH - len("QA") - 1
UNIT_SERIAL_CHARS = string.digits + string.ascii_uppercase
HSN_SERIAL_CHARS = string.digits


@dataclass(frozen=True)
class UnitSpec:
    name: str
    uqc: str


@dataclass(frozen=True)
class HsnSpec:
    code: str
    name: str


class UnitHsnDataFactory:
    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._unit_serial = count(1)
        self._hsn_serial = count(1)

    def unit(self, uqc: str = BOX_UQC) -> UnitSpec:
        return UnitSpec(self.unit_name(), uqc)

    def unit_name(self) -> str:
        serial = _serial_char(next(self._unit_serial), UNIT_SERIAL_CHARS, "unit names")
        return f"QA{self._run_id[:UNIT_RUN_ID_CHARS]}{serial}"

    def hsn(self) -> HsnSpec:
        serial = next(self._hsn_serial)
        return HsnSpec(self._hsn_code(serial), f"QA-{self._run_id}-HSN{serial}")

    def _hsn_code(self, serial: int) -> str:
        body_digits = HSN_CODE_LENGTH - len(HSN_LEADING_DIGIT) - HSN_SERIAL_DIGITS
        body = int(self._run_id, HEX_BASE) % 10**body_digits
        return (
            f"{HSN_LEADING_DIGIT}{body:0{body_digits}d}{_serial_char(serial, HSN_SERIAL_CHARS, 'HSN codes')}"
        )


def _serial_char(serial: int, alphabet: str, what: str) -> str:
    """One character per serial; serial len(alphabet) wraps to the first character, which is still unused."""
    if serial > len(alphabet):
        raise ValueError(f"only {len(alphabet)} {what} fit per factory; use a new run id for more")
    return alphabet[serial % len(alphabet)]
