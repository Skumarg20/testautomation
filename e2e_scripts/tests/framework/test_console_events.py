"""F03-R34: the console_events plugin, run as a real pytest on a tiny temp suite (no app needed)."""

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.framework

E2E_DIR = Path(__file__).resolve().parents[2]
PLUGIN = "plugins.console_events"
SECRET = "S3cret!pw"
ANY_TIME = 120

PASS_FAIL_SKIP = """
    import pytest

    def test_passes():
        assert True

    def test_fails():
        assert 1 == 2, "boom"

    def test_skips():
        pytest.skip("not today")

    @pytest.mark.xfail(reason="known")
    def test_xfails():
        assert False

    @pytest.mark.xfail(reason="odd")
    def test_xpasses():
        assert True

    @pytest.fixture
    def broken():
        raise RuntimeError("fixture exploded")

    def test_setup_error(broken):
        pass
"""


def make_suite(tmp_path: Path, source: str, *, with_plugin: bool = True) -> Path:
    suite = tmp_path / "suite"
    suite.mkdir()
    (suite / "pytest.ini").write_text("[pytest]\naddopts = -p no:cacheprovider\n")
    (suite / "test_sample.py").write_text(textwrap.dedent(source))
    if with_plugin:
        shutil.copytree(E2E_DIR / "plugins", suite / "plugins", ignore=shutil.ignore_patterns("__pycache__"))
    return suite


def run_pytest(suite: Path, *args: str, events: Path | None, extra_env: dict[str, str] | None = None) -> Any:
    env = {k: v for k, v in os.environ.items() if not k.startswith("CONSOLE_")}
    if events is not None:
        env["CONSOLE_EVENTS_FILE"] = str(events)
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", PLUGIN, *args],
        cwd=suite,
        env=env,
        capture_output=True,
        text=True,
        timeout=ANY_TIME,
        check=False,
    )


def read_events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def of_type(events: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [e for e in events if e["t"] == kind]


def many_tests(count: int) -> str:
    return "import pytest\n\n" + "\n".join(f"def test_case_{n}():\n    assert True\n" for n in range(count))


def test_plugin_inert_without_console_events_file(tmp_path: Path) -> None:
    suite = make_suite(tmp_path, many_tests(2))

    done = run_pytest(suite, "-q", events=None)

    assert done.returncode == 0, done.stdout
    assert "2 passed" in done.stdout
    assert not list(suite.rglob("*.jsonl"))


def test_plugin_loads_with_python_dash_m_pytest_and_fails_with_bare_pytest(tmp_path: Path) -> None:
    suite = make_suite(tmp_path, many_tests(1))
    events = tmp_path / "live" / "run.jsonl"
    bare = Path(sys.executable).parent / "pytest"

    with_module = run_pytest(suite, "-q", events=events)
    env = {**os.environ, "CONSOLE_EVENTS_FILE": str(events)}
    env.pop("PYTHONPATH", None)
    with_bare = subprocess.run(
        [str(bare), "-p", PLUGIN, "-q"],
        cwd=suite,
        env=env,
        capture_output=True,
        text=True,
        timeout=ANY_TIME,
        check=False,
    )

    assert with_module.returncode == 0
    assert events.exists()
    assert with_bare.returncode != 0
    assert "ModuleNotFoundError" in with_bare.stdout + with_bare.stderr


def test_plugin_writes_each_start_end_collected_session_end_once_with_n4(tmp_path: Path) -> None:
    suite = make_suite(tmp_path, many_tests(12))
    events = tmp_path / "run.jsonl"

    done = run_pytest(suite, "-q", "-n", "4", events=events)

    assert done.returncode == 0, done.stdout
    lines = read_events(events)
    assert len(of_type(lines, "collected")) == 1
    assert of_type(lines, "collected")[0]["total"] == 12
    assert len(of_type(lines, "session_end")) == 1
    assert of_type(lines, "session_end")[0]["exitstatus"] == 0
    starts = [e["nodeid"] for e in of_type(lines, "start")]
    ends = [e["nodeid"] for e in of_type(lines, "end")]
    assert sorted(starts) == sorted(set(starts))
    assert len(starts) == 12
    assert sorted(ends) == sorted(set(ends))
    assert len(ends) == 12
    queued = [n for e in of_type(lines, "queued") for n in e["nodeids"]]
    assert sorted(queued) == sorted(starts)
    assert lines[-1]["t"] == "session_end"


def test_plugin_worker_ids_gw0_to_gw3_with_n4_and_gw0_without_n(tmp_path: Path) -> None:
    suite = make_suite(tmp_path, many_tests(20))
    distributed, serial = tmp_path / "n4.jsonl", tmp_path / "n0.jsonl"

    run_pytest(suite, "-q", "-n", "4", events=distributed)
    run_pytest(suite, "-q", events=serial)

    workers = {e["worker"] for e in of_type(read_events(distributed), "end")}
    assert workers <= {"gw0", "gw1", "gw2", "gw3"}
    assert len(workers) > 1
    assert {e["worker"] for e in of_type(read_events(serial), "end")} == {"gw0"}
    assert len(of_type(read_events(serial), "collected")) == 1


def test_plugin_reports_outcomes_durations_and_failure_log_lines(tmp_path: Path) -> None:
    suite = make_suite(tmp_path, PASS_FAIL_SKIP)
    events = tmp_path / "run.jsonl"

    run_pytest(suite, "-q", events=events)

    lines = read_events(events)
    outcome = {e["nodeid"].split("::")[1]: e for e in of_type(lines, "end")}
    assert {name: e["outcome"] for name, e in outcome.items()} == {
        "test_passes": "passed",
        "test_fails": "failed",
        "test_skips": "skipped",
        "test_xfails": "xfailed",
        "test_xpasses": "xpassed",
        "test_setup_error": "failed",
    }
    assert outcome["test_setup_error"]["setupError"] is True
    assert "boom" in outcome["test_fails"]["message"]
    assert outcome["test_skips"]["skipReason"] == "not today"
    assert all(isinstance(e["durationMs"], int) and e["durationMs"] >= 0 for e in outcome.values())
    logs = {(e["level"], e.get("nodeid", "").split("::")[-1]) for e in of_type(lines, "log")}
    assert ("FAIL", "test_fails") in logs
    assert ("ERROR", "test_setup_error") in logs
    assert of_type(lines, "session_end")[0]["exitstatus"] == 1


def test_plugin_order_is_start_then_log_then_end_for_one_test(tmp_path: Path) -> None:
    suite = make_suite(tmp_path, PASS_FAIL_SKIP)
    events = tmp_path / "run.jsonl"

    run_pytest(suite, "-q", events=events)

    lines = [e for e in read_events(events) if e.get("nodeid", "").endswith("::test_fails")]
    assert [e["t"] for e in lines] == ["start", "log", "end"]


def test_plugin_worker_crash_writes_failed_end_from_controller(tmp_path: Path) -> None:
    source = """
        import os

        def test_ok():
            assert True

        def test_crashes_the_worker():
            os._exit(13)
    """
    suite = make_suite(tmp_path, source)
    events = tmp_path / "run.jsonl"

    run_pytest(suite, "-q", "-n", "2", events=events)

    lines = read_events(events)
    ends = [e for e in of_type(lines, "end") if e["nodeid"].endswith("test_crashes_the_worker")]
    assert len(ends) == 1
    assert ends[0]["outcome"] == "failed"
    assert ends[0]["worker"] in {"gw0", "gw1", "gw2"}
    crash_logs = [e for e in of_type(lines, "log") if "crashed while running" in e["message"]]
    assert crash_logs
    assert crash_logs[0]["level"] == "ERROR"
    assert len(of_type(lines, "session_end")) == 1


def test_flaky_rerun_outcome_flaky_counts_as_passed(tmp_path: Path) -> None:
    source = """
        from pathlib import Path

        def test_passes_on_second_try():
            marker = Path("attempts.txt")
            tries = int(marker.read_text()) if marker.exists() else 0
            marker.write_text(str(tries + 1))
            assert tries >= 1
    """
    suite = make_suite(tmp_path, source)
    events = tmp_path / "run.jsonl"

    done = run_pytest(suite, "-q", "--reruns", "2", events=events)

    assert done.returncode == 0, done.stdout
    ends = of_type(read_events(events), "end")
    assert [e["outcome"] for e in ends] == ["rerun", "flaky"]
    assert len(of_type(read_events(events), "start")) == 2


def test_plugin_masks_secret_values_before_writing(tmp_path: Path) -> None:
    source = f"""
        def test_leaks_secret():
            assert "x" == "{SECRET}"
    """
    suite = make_suite(tmp_path, source)
    secrets = tmp_path / "secrets.json"
    secrets.write_text(json.dumps([SECRET]))
    events = tmp_path / "run.jsonl"

    run_pytest(suite, "-q", events=events, extra_env={"CONSOLE_SECRET_VALUES_FILE": str(secrets)})

    text = events.read_text()
    assert SECRET not in text
    assert "***" in text


def test_plugin_flushes_each_line_while_the_test_is_still_running(tmp_path: Path) -> None:
    source = """
        import os
        from pathlib import Path

        def test_reads_own_start_line():
            text = Path(os.environ["CONSOLE_EVENTS_FILE"]).read_text()
            assert '"t":"start"' in text
            assert '"t":"collected"' in text
    """
    suite = make_suite(tmp_path, source)

    done = run_pytest(suite, "-q", events=tmp_path / "run.jsonl")

    assert done.returncode == 0, done.stdout


def test_plugin_survives_an_unwritable_events_file(tmp_path: Path) -> None:
    suite = make_suite(tmp_path, many_tests(2))
    blocked = tmp_path / "file-not-dir"
    blocked.write_text("x")

    done = run_pytest(suite, "-q", events=blocked / "run.jsonl")

    assert done.returncode == 0, done.stdout
    assert "2 passed" in done.stdout


def test_plugin_lines_stay_below_4kb_and_long_ids_are_chunked(tmp_path: Path) -> None:
    names = "\n".join(f"def test_{'x' * 120}_{n}():\n    assert True\n" for n in range(80))
    suite = make_suite(tmp_path, names)
    events = tmp_path / "run.jsonl"

    run_pytest(suite, "-q", events=events)

    raw = events.read_bytes().splitlines()
    assert max(len(line) for line in raw) < 4096
    queued = [n for e in of_type(read_events(events), "queued") for n in e["nodeids"]]
    assert len(queued) == 80
