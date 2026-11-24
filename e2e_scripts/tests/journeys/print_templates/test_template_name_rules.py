"""J32 Template designer: the template name rules (specs/template-designer.md TD-06, TD-07)."""

import re

import pytest

from pages.print_templates.owned_templates import SALE_BILL, SOURCE_TEMPLATE, OwnedTemplates
from pages.print_templates.template_customize import TemplateCustomizePage

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("template-designer"),
    pytest.mark.xdist_group("garments-print-templates"),
]

NAME_REQUIRED = re.compile("template name required", re.IGNORECASE)


def test_template_without_a_name_is_refused(customize: TemplateCustomizePage) -> None:
    customize.open_for(SALE_BILL)
    studio = customize.customise_predefined(SOURCE_TEMPLATE)

    studio.save_as_template("")

    studio.expect_refused_saying(NAME_REQUIRED)
    studio.close()


def test_second_template_with_the_same_name_is_not_saved(
    templates: OwnedTemplates, customize: TemplateCustomizePage, run_id: str
) -> None:
    """The API has a CheckDuplicate(reporttype, name) endpoint (scenario TD-07); one name, one template.

    The two saves carry different titles, so a silent overwrite (still one card) fails on the kept title."""
    name, first_title = templates.new_name(), f"QA-{run_id}-First"
    save_titled_copy(customize, name, first_title)
    customize.open_for(SALE_BILL)
    studio = customize.customise_predefined(SOURCE_TEMPLATE)
    studio.enter_title(f"QA-{run_id}-Second")

    studio.save_as_template(name)

    customize.open_for(SALE_BILL)
    customize.expect_custom_template_count(name, 1)
    kept = customize.customise_custom(name)
    kept.expect_title(first_title)
    kept.close()


def save_titled_copy(customize: TemplateCustomizePage, name: str, title: str) -> None:
    customize.open_for(SALE_BILL)
    studio = customize.customise_predefined(SOURCE_TEMPLATE)
    studio.enter_title(title)
    studio.save_as_template(name)
    studio.expect_saved()
