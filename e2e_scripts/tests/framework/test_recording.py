"""Recording switch: a test's browser contexts record video only when a folder is given."""

from pathlib import Path

import pytest

from fixtures.session import recording_folder_for, with_recording

pytestmark = pytest.mark.framework


def test_options_without_a_folder_stay_unchanged() -> None:
    options = {"viewport": {"width": 1280, "height": 720}}
    assert with_recording(options, None) == options


def test_options_with_a_folder_record_video_into_it(tmp_path: Path) -> None:
    options = with_recording({"locale": "en-IN"}, tmp_path)
    assert options["record_video_dir"] == str(tmp_path)
    assert options["locale"] == "en-IN"


def test_folder_is_named_after_the_test_and_safe_on_disk() -> None:
    folder = recording_folder_for(Path("results/recordings"), "tests/a.py::test_x[chromium-/sale]")
    assert folder.parent == Path("results/recordings")
    assert not set(folder.name) & set("/:[]")
