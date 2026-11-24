"""Parallel workers must not share one login: each worker picks its own user from the account pool."""

import pytest

from config.settings import Credentials, Settings, worker_index
from fixtures.session import auth_file_stem

pytestmark = pytest.mark.framework

CHEMIST_POOL = '{"chemist": [["user0", "pass0"], ["user1", "pass1"], ["user2", "pass2"]]}'


@pytest.fixture
def pool_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("QA_POOL", CHEMIST_POOL)
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_worker_index_reads_the_number_of_an_xdist_worker() -> None:
    assert worker_index("gw17") == 17


def test_worker_index_of_a_run_without_xdist_is_zero() -> None:
    assert worker_index("master") == 0


def test_each_worker_gets_a_different_user_while_the_pool_lasts(pool_settings: Settings) -> None:
    credentials = [pool_settings.credentials("chemist", worker_index=index) for index in range(3)]
    assert credentials == [
        Credentials("user0", "pass0"),
        Credentials("user1", "pass1"),
        Credentials("user2", "pass2"),
    ]


def test_workers_beyond_the_pool_size_wrap_around(pool_settings: Settings) -> None:
    assert pool_settings.credentials("chemist", worker_index=4) == Credentials("user1", "pass1")


def test_single_account_without_a_pool_is_used_by_every_worker() -> None:
    settings = Settings(_env_file=None, qa_chemist_user="solo", qa_chemist_pass="secret")  # type: ignore[call-arg]
    assert settings.credentials("chemist", worker_index=9) == Credentials("solo", "secret")


def test_account_missing_from_pool_and_env_has_no_credentials(pool_settings: Settings) -> None:
    assert pool_settings.credentials("pharma", worker_index=0) is None


def test_auth_files_of_two_processes_never_collide() -> None:
    assert auth_file_stem("gw0", "chemist", process_id=1) != auth_file_stem("gw0", "chemist", process_id=2)
