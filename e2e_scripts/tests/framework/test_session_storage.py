import json
from pathlib import Path

import pytest

from fixtures.session import _drop_per_tab_keys

pytestmark = pytest.mark.framework


def test_per_tab_lock_is_removed_from_saved_state_and_other_keys_stay(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    entries = [{"name": "app-tab-lock", "value": "1"}, {"name": "access_token", "value": "t"}]
    state_file.write_text(json.dumps({"cookies": [], "origins": [{"origin": "x", "localStorage": entries}]}))

    _drop_per_tab_keys(state_file)

    kept = json.loads(state_file.read_text())["origins"][0]["localStorage"]
    assert kept == [{"name": "access_token", "value": "t"}]
