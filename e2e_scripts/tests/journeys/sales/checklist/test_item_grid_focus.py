"""Sale checklist rows 13 to 18, 38 (product half) and 58: the cursor in the item grid of a new sale bill.

Components: `processout.transaction.component.ts` (PO), the item list
`Component/Master/Item/itemmaster.component.ts` (IM) and the batch/multi-unit cell editors in
`childcomponents/`. The test item is 44646015 with batch 1231231123 (pharma company). Nothing is saved."""

import pytest
from playwright.sync_api import expect

from pages.sale.checklist.bill_screen import STANDARD_LINE, ChecklistBill
from pages.sale.checklist.focus import IN_A_WINDOW, grid_column
from pages.sale.checklist.sale_setting import CURSOR_WAIT, setting_held
from pages.sale.documents.item_grid import BATCH, PRODUCT, QUANTITY

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("sale-bill-creation"),
    pytest.mark.xdist_group("chemist-tenant"),
]

UNIT_2 = "unitFromEnteredValue"  # PO:1721 sets its header to "Unit-2"; the quantity column is unit 1
CURSOR_WAIT_ALL = "1"  # PO:12389-12403: "1 : All 2: Qty"
CURSOR_WAIT_QTY = "2"
ASK = "1"


@pytest.fixture
def party_chosen(bill: ChecklistBill) -> ChecklistBill:
    bill.choose_standard_party()
    return bill


def open_item_list(bill: ChecklistBill, row: int) -> None:
    bill.document.grid.cell(row, PRODUCT).click()
    expect(bill.pick_list).to_be_visible()


def test_item_list_opens_with_the_cursor_in_its_search_box(party_chosen: ChecklistBill) -> None:
    """Row 13: IM:1826 and IM:2020 focus the item list's search box when it opens."""
    open_item_list(party_chosen, 0)

    expect(party_chosen.pick_list.get_by_role("searchbox")).to_be_focused()


def test_item_list_highlights_the_item_added_last(party_chosen: ChecklistBill) -> None:
    """Row 14: the window is given lastSelectedItem (PO:8862) and IM:871-875 selects that row when it
    opens."""
    party_chosen.add_standard_line(0)
    added_item = party_chosen.product_cell(0).inner_text().strip()

    open_item_list(party_chosen, 1)

    selected = party_chosen.pick_list.locator(".ag-row-selected")
    expect(selected.first).to_contain_text(added_item, ignore_case=True)


def test_product_search_finds_the_item_by_its_code(party_chosen: ChecklistBill) -> None:
    """Row 38: typing the item code in the item list's Itemcode mode lists that item."""
    open_item_list(party_chosen, 0)
    window = party_chosen.pick_list

    window.get_by_role("combobox").first.select_option("Itemcode")
    window.get_by_role("searchbox").press_sequentially(STANDARD_LINE.product)

    expect(window.locator('[col-id="itemcode"]').filter(has_text=STANDARD_LINE.product).first).to_be_visible()


def test_after_the_item_the_cursor_goes_to_batch_expiry_or_quantity(party_chosen: ChecklistBill) -> None:
    """Row 15: once an item is chosen the cursor goes to the batch (when batches apply), else the expiry, else
    the quantity (PO:7261 sends the cursor to the batch window while batchLinkID is empty and
    isBatchApplicable())."""
    party_chosen.document.grid.select_product(0, STANDARD_LINE.product)

    party_chosen.focus.expect_at(
        IN_A_WINDOW, grid_column(BATCH), grid_column("expiryDate"), grid_column(QUANTITY)
    )


def test_batch_window_lists_the_batch_and_picking_it_fills_the_batch_cell(
    party_chosen: ChecklistBill,
) -> None:
    """Row 16: for an item with batches the batch window opens and the batch picked lands in the grid row."""
    grid = party_chosen.document.grid
    grid.select_product(0, STANDARD_LINE.product)
    expect(party_chosen.page.locator('[col-id="batchName"]').first).to_be_visible()

    grid.choose_batch(0, STANDARD_LINE.batch)

    expect(grid.cell(0, BATCH)).to_contain_text(STANDARD_LINE.batch)


def test_after_the_batch_is_picked_the_cursor_is_in_the_quantity_cell(party_chosen: ChecklistBill) -> None:
    """Row 17: PO:7458 / the batch editor hand the cursor to quantity (or to Unit-2 first when multi-unit is
    on, see row 18)."""
    grid = party_chosen.document.grid
    grid.select_product(0, STANDARD_LINE.product)
    grid.choose_batch(0, STANDARD_LINE.batch)

    party_chosen.focus.expect_at(grid_column(QUANTITY), grid_column(UNIT_2))


def test_with_multi_unit_on_the_cursor_visits_unit_2_before_unit_1(party_chosen: ChecklistBill) -> None:
    """Row 18: PO:7458 enters "unitFromEnteredValue" (Unit-2) when multiUnitControls.isMultiUnitOn == "T", and
    Enter then moves on to the quantity (Unit-1) column. Skipped when the grid has no Unit-2 column."""
    grid = party_chosen.document.grid
    grid.select_product(0, STANDARD_LINE.product)
    grid.choose_batch(0, STANDARD_LINE.batch)
    if grid.cell(0, UNIT_2).count() == 0:
        pytest.skip("row 18: needs Control Room multi-unit on; the grid has no Unit-2 column")

    party_chosen.focus.expect_at(grid_column(UNIT_2))
    party_chosen.page.keyboard.press("Enter")

    party_chosen.focus.expect_at(grid_column(QUANTITY))


@pytest.mark.parametrize(
    ("wait_value", "stays_on_row"),
    [(CURSOR_WAIT_ALL, True), (CURSOR_WAIT_QTY, False)],
    ids=["wait-on-all", "wait-on-qty"],
)
def test_cursor_wait_decides_whether_the_cursor_leaves_the_row_after_the_quantity(
    bill: ChecklistBill, wait_value: str, stays_on_row: bool
) -> None:
    """Row 58: with "Cursor wait on" = Qty and a rate above zero the cursor jumps to the next line after the
    quantity (PO:12397 cursorWaitOnWhichFieldSetting, PO:12755 / 12819 "2 //QUANTITY"); with All it keeps
    walking the row's own columns. Rate comes from the item, quantity 1."""
    with setting_held(bill, CURSOR_WAIT, wait_value):
        bill.reopen()
        bill.choose_standard_party()
        grid = bill.document.grid
        grid.select_product(0, STANDARD_LINE.product)
        grid.choose_batch(0, STANDARD_LINE.batch)

        grid.enter_quantity(0, STANDARD_LINE.quantity)

        bill.focus.expect_in_grid_row(0 if stays_on_row else 1)
