"""
Proves the Layer 0 harness itself works: server starts against sandboxed
data, serves it back over HTTP, and is fully isolated from the real
data/genealogy_new_model.json.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_server_serves_sandboxed_state(live_server):
    state = live_server.get_state()

    assert "persons" in state
    assert "events" in state
    assert "event_participations" in state
    assert len(state["persons"]) > 0


def test_sandbox_is_isolated_from_real_data(live_server):
    real_data_path = REPO_ROOT / "data" / "genealogy_new_model.json"
    sandboxed_data_path = live_server.sandbox_dir / "data" / "genealogy_new_model.json"

    assert sandboxed_data_path.exists()
    assert sandboxed_data_path != real_data_path
    assert sandboxed_data_path.stat().st_size == real_data_path.stat().st_size
