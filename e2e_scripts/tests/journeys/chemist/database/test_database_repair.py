import pytest

from pages.settings.database_repair import DatabaseRepair

pytestmark = [
    pytest.mark.p2,
    pytest.mark.journey("database-repair"),
    pytest.mark.xdist_group("chemist-tenant"),
]


def test_database_repair_runs_to_completion(database_repair: DatabaseRepair) -> None:
    database_repair.repair()
