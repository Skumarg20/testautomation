"""Custom print templates a test creates, named `QA-<run_id>-Tpl-<n>`, and their clean-up.

Saving a custom template makes it the default of its voucher type (specs/template-designer.md, NEEDS
DECISION 1), so whatever a test created is deleted in teardown, every copy of a name included.
"""

from functools import partial
from itertools import count

from playwright.sync_api import Page

from pages.components.undo import undo_all
from pages.print_templates.template_customize import TemplateCustomizePage

SALE_BILL = "Sale Bill"
# The built-in Sale Bill format the tests copy; observed in the predefined list on 2026-10-09.
SOURCE_TEMPLATE = "Full-Page"


class OwnedTemplates:
    def __init__(self, page: Page, run_id: str) -> None:
        self._screen = TemplateCustomizePage(page)
        self._run_id = run_id
        self._serial = count(1)
        self._names: list[str] = []

    def new_name(self) -> str:
        name = f"QA-{self._run_id}-Tpl-{next(self._serial)}"
        self._names.append(name)
        return name

    def create_copy(self, name: str) -> None:
        """Saves a copy of the source Sale Bill template under `name`, unchanged."""
        self._screen.open_for(SALE_BILL)
        studio = self._screen.customise_predefined(SOURCE_TEMPLATE)
        studio.save_as_template(name)
        studio.expect_saved()

    def delete_all(self) -> None:
        undo_all((name, partial(self._delete_every_copy, name)) for name in self._names)

    def _delete_every_copy(self, name: str) -> None:
        """Deletes the copies counted once; each delete must take effect, so a stuck delete fails the
        teardown instead of looping."""
        self._screen.open_for(SALE_BILL)
        copies = self._screen.custom_template_count(name)
        for left in reversed(range(copies)):
            self._screen.delete_custom(name)
            self._screen.open_for(SALE_BILL)
            self._screen.expect_custom_template_count(name, left)
