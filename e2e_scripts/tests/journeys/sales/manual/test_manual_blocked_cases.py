"""Manual cases of "Sale Bill (Ajay)" that the QA data and the page objects cannot support yet.

Each skip names the rows, the rule that was found (file:line in newmarg-webangular20/src/app) and exactly
what is missing, so that supplying it turns the stub into a test. Nothing here guesses data or locators.
"""

import pytest

pytestmark = [pytest.mark.p2, pytest.mark.journey("sale-bill-creation")]
