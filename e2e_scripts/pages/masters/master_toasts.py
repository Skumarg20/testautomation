"""Toasts with a given text, for the warning and error toasts the master screens raise."""

from re import Pattern

from playwright.sync_api import expect

from pages.accounting.toasts import WARNING_TIMEOUT_MS, Toasts


class MasterToasts(Toasts):
    def expect_warning_saying(self, message: Pattern[str]) -> None:
        expect(self._toast("warning")).to_contain_text(message, timeout=WARNING_TIMEOUT_MS)

    def expect_error_saying(self, message: Pattern[str]) -> None:
        expect(self._toast("error")).to_contain_text(message, timeout=WARNING_TIMEOUT_MS)
