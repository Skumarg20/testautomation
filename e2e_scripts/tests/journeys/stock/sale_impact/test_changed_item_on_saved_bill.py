"""Stock row 26: replacing item A by item B on a saved bill restores A's stock and takes B's."""

import pytest

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("sale-bill-modification"),
    pytest.mark.xdist_group("chemist-tenant"),
]
