"""J37 Control Room > "Store Setting": its one option, Rate Selection, and how the window closes.

The fixtures hold the tenant-wide "Store Setting" row at Yes and restore the rate a test changes.
"""

import pytest

from pages.online_store.store_setting import StoreSettingWindow
from test_data.online_store import MRP_RATE, RATE_CAPTIONS, RATE_SELECTION, STORE_SETTING_COLUMNS

# The fixtures change and restore a tenant-wide Control Room option (CLAUDE.md rule 0).
pytestmark = [
    pytest.mark.p3,
    pytest.mark.journey("online-store"),
    pytest.mark.xdist_group("chemist-tenant"),
]


def test_store_setting_window_has_the_settings_columns(store_setting: StoreSettingWindow) -> None:
    """OS-08: columns S.No., Particulars, Action, Help."""
    store_setting.open()
    assert tuple(store_setting.column_headers()) == STORE_SETTING_COLUMNS


def test_store_setting_window_offers_only_rate_selection(store_setting: StoreSettingWindow) -> None:
    """OS-08, OS-13: one row, Rate Selection; the five commented-out options are not rendered."""
    store_setting.open()
    assert store_setting.particulars() == [RATE_SELECTION]


def test_rate_selection_offers_mrp_and_rates_a_to_h(store_setting: StoreSettingWindow) -> None:
    """OS-09: M.R.P, Rate A ... Rate H (captions may follow the company's rate captions: verify live)."""
    store_setting.open()
    assert tuple(store_setting.rate_options()) == RATE_CAPTIONS


def test_chosen_rate_is_kept_after_saving_the_control_room(rate_restored: StoreSettingWindow) -> None:
    """OS-10: M.R.P chosen, Control Room saved, window opened again: still M.R.P (MBC-2591: not saved)."""
    rate_restored.open()
    rate_restored.choose_rate(MRP_RATE)
    rate_restored.close_with_cross()
    rate_restored.save_control_room()
    rate_restored.page.reload()
    rate_restored.open()
    assert rate_restored.chosen_rate() == MRP_RATE


def test_store_setting_window_has_no_save_button(store_setting: StoreSettingWindow) -> None:
    """OS-12: the footer is commented out (MB-34343 "only see a CLOSE button"); records today's state."""
    store_setting.open()
    assert store_setting.save_button_in_window.count() == 0


def test_store_setting_window_closes_with_escape(store_setting: StoreSettingWindow) -> None:
    """OS-12: Esc closes the window (online-store-setting.component.ts:85-89)."""
    store_setting.open()
    store_setting.close_with_escape()
    store_setting.expect_closed()


def test_store_setting_window_closes_with_the_cross(store_setting: StoreSettingWindow) -> None:
    """OS-12: × closes the window."""
    store_setting.open()
    store_setting.close_with_cross()
    store_setting.expect_closed()
