"""Test data of the J13 stock movement journey."""

from dataclasses import replace
from decimal import Decimal

from test_data.factory import DataFactory
from test_data.models import ItemMasterSpec

OPENING_QUANTITY = Decimal(10)
MAIN_STORE = "Main Store"
SCRAP_STORE = "Scrap Store"


def stock_item(data: DataFactory, run_id: str) -> ItemMasterSpec:
    """A new item named for this journey, so a reader of the tenant can tell where it came from."""
    return replace(data.item_master(), product=f"QA-{run_id}-Stock")
