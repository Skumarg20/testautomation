"""Round-off rule of the sale bill and the Control Room option that selects it.

Control Room > Configure > "Round Off Required in Sale ?" has four values (KB MBRound_off: No, Auto, Upper,
Lower; code 0 none, 1 normal, 2 upper, 3 lower, processout.transaction.component.ts:10524-10590). Normal is
`Math.round`, upper `Math.ceil`, lower `Math.floor` of the invoice value.
"""

from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal
from enum import Enum

OPTION_NAME = "Round Off Required in Sale"
TWO_PLACES = Decimal("0.01")


class RoundOff(Enum):
    NO = "No"
    AUTO = "Auto"
    UPPER = "Upper"
    LOWER = "Lower"


def invoice_after_round_off(value: Decimal, mode: RoundOff) -> Decimal:
    whole = Decimal(1)
    if mode is RoundOff.NO:
        return value.quantize(TWO_PLACES, ROUND_HALF_UP)
    rounding = {RoundOff.AUTO: ROUND_HALF_UP, RoundOff.UPPER: ROUND_CEILING, RoundOff.LOWER: ROUND_FLOOR}[
        mode
    ]
    return value.quantize(whole, rounding)
