"""Sale bill discount in amount/percent switched on for a test (needed by a Bill Value scheme).

applySchemeDiscount works only when `saleBillDiscount` and `saleBillDiscountInAmount` are on
(Scheme.businesslogic.ts:1066-1070, :1112-1114). The window is the sale-bill-discount Configure window
(BillDiscountConfiguration); it opens from an open sale bill. The original switches are written back.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from pages.settings.bill_discount_configuration import BillDiscountConfiguration, BillDiscountSwitches


@contextmanager
def bill_discount_on(configuration: BillDiscountConfiguration) -> Iterator[None]:
    original = configuration.current_switches()
    configuration.apply(BillDiscountSwitches(True, original.discount2, True))
    try:
        yield
    finally:
        configuration.apply(original)
