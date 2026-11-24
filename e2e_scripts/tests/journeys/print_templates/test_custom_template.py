"""J32 Template designer: copy a built-in Sale Bill template, edit, rename and delete the copy.

Spec: specs/template-designer.md (TD-02..TD-05, TD-08). Each test copies the built-in "Full-Page" template
under its own `QA-<run_id>-Tpl-<n>` name; the `templates` fixture deletes every copy in teardown.
"""

import pytest

from pages.print_templates.owned_templates import SALE_BILL, SOURCE_TEMPLATE, OwnedTemplates
from pages.print_templates.template_customize import TemplateCustomizePage

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("template-designer"),
    # A saved custom template becomes the Sale Bill default of the company, so these tests run one at a time.
    pytest.mark.xdist_group("garments-print-templates"),
]

# The Item Table column the tests add: field id and the header the preview shows (both seen live).
FREE_COLUMN = "free"
FREE_HEADER = "Free"


def test_copy_of_built_in_template_is_listed_as_custom(
    templates: OwnedTemplates, customize: TemplateCustomizePage
) -> None:
    name = templates.new_name()

    templates.create_copy(name)

    customize.open_for(SALE_BILL)
    customize.expect_custom_template(name)


def test_added_item_column_shows_in_the_preview(customize: TemplateCustomizePage) -> None:
    customize.open_for(SALE_BILL)
    studio = customize.customise_predefined(SOURCE_TEMPLATE)
    studio.expect_no_preview_column(FREE_HEADER)

    studio.show_item_column(FREE_COLUMN)

    studio.expect_preview_column(FREE_HEADER)
    studio.close()


def test_added_item_column_is_kept_after_saving(
    templates: OwnedTemplates, customize: TemplateCustomizePage
) -> None:
    name = templates.new_name()
    customize.open_for(SALE_BILL)
    studio = customize.customise_predefined(SOURCE_TEMPLATE)
    studio.show_item_column(FREE_COLUMN)
    studio.save_as_template(name)
    studio.expect_saved()

    customize.open_for(SALE_BILL)
    reopened = customize.customise_custom(name)

    reopened.expect_item_column_ticked(FREE_COLUMN)
    reopened.expect_preview_column(FREE_HEADER)
    reopened.close()


def test_edited_title_is_kept_after_saving(
    templates: OwnedTemplates, customize: TemplateCustomizePage, run_id: str
) -> None:
    name = templates.new_name()
    title = f"QA-{run_id}-Title"
    customize.open_for(SALE_BILL)
    studio = customize.customise_predefined(SOURCE_TEMPLATE)
    studio.enter_title(title)
    studio.save_as_template(name)
    studio.expect_saved()

    customize.open_for(SALE_BILL)
    reopened = customize.customise_custom(name)

    reopened.expect_title(title)
    reopened.close()


def test_renamed_template_is_listed_under_the_new_name_only(
    templates: OwnedTemplates, customize: TemplateCustomizePage
) -> None:
    old_name, new_name = templates.new_name(), templates.new_name()
    templates.create_copy(old_name)
    customize.open_for(SALE_BILL)
    studio = customize.customise_custom(old_name)

    studio.save_as_template(new_name)
    studio.expect_saved()

    customize.open_for(SALE_BILL)
    customize.expect_custom_template(new_name)
    customize.expect_no_custom_template(old_name)


def test_deleted_template_leaves_the_list(
    templates: OwnedTemplates, customize: TemplateCustomizePage
) -> None:
    name = templates.new_name()
    templates.create_copy(name)
    customize.open_for(SALE_BILL)

    customize.delete_custom(name)

    customize.open_for(SALE_BILL)
    customize.expect_no_custom_template(name)


def test_declined_deletion_keeps_the_template(
    templates: OwnedTemplates, customize: TemplateCustomizePage
) -> None:
    name = templates.new_name()
    templates.create_copy(name)
    customize.open_for(SALE_BILL)

    customize.ask_to_delete_custom(name)
    customize.decline_deletion()

    customize.open_for(SALE_BILL)
    customize.expect_custom_template(name)
