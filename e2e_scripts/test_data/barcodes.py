"""Test data of the J27 barcode journey: per-test barcodes and item names."""

from dataclasses import replace
from decimal import Decimal

from test_data.factory import DataFactory
from test_data.models import ItemMasterSpec

# A leading 8 keeps the code clear of the tenant's automatic 8-digit pattern (11110001, ...).
BARCODE_PREFIX = "8"
# Ten digits in all: the Print Barcode "Select Item" search box kept only the first ten of an
# eleven-digit code (run local-1010, HR-002), so the search found nothing.
BARCODE_DIGITS = 9
OPENING_QUANTITY = Decimal(10)
SALE_PARTY = "Ajay"


def item_barcode(run_id: str) -> str:
    """Ten digits derived from the run id, so each test has its own barcode."""
    return BARCODE_PREFIX + str(int(run_id, 16)).zfill(BARCODE_DIGITS)[-BARCODE_DIGITS:]


def barcode_item(data: DataFactory, run_id: str) -> ItemMasterSpec:
    return replace(data.item_master(), product=f"QA-{run_id}-Barcode")


def twin_item(data: DataFactory, run_id: str) -> ItemMasterSpec:
    """A second item of the same test, meant to carry the first item's barcode."""
    return replace(data.item_master(), product=f"QA-{run_id}-Twin")
