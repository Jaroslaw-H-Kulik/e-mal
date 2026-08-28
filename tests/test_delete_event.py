"""
Layer 1 golden-master tests for POST /api/delete-event.
See test_add_relationship.py for the fixture-comparison pattern.
"""
import anchors
from golden_utils import assert_matches_golden, assert_no_new_invariant_issues, state_diff


def _run(live_server, name, payload):
    before = live_server.get_state()
    response = live_server.post("/api/delete-event", payload).json()
    after = live_server.get_state()

    assert_no_new_invariant_issues(before, after)
    assert_matches_golden(name, {"response": response, "diff": state_diff(before, after)})
    return response, before, after


def test_deletes_event_and_all_its_participations(live_server):
    """E0055 is a plain birth event with 3 participants (child/father/
    mother) and no cascading side effects - deleting it removes the event
    plus exactly those 3 participations; persons themselves are untouched
    (delete_event never touches the persons collection, unlike
    delete_person which cascades the other direction)."""
    payload = {"event_id": anchors.DELETE_EVENT_ID}
    response, before, after = _run(live_server, "delete_event_removes_participations", payload)
    assert response["success"] is True
    assert response["deleted_participations"] == 3
    assert anchors.DELETE_EVENT_ID not in after["events"]
    assert after["persons"] == before["persons"]


def test_nonexistent_event_fails_cleanly(live_server):
    payload = {"event_id": anchors.NONEXISTENT_EVENT_ID}
    before = live_server.get_state()
    response = live_server.post("/api/delete-event", payload).json()
    after = live_server.get_state()

    assert response == {"success": False, "error": "Event not found"}
    diff = state_diff(before, after)
    assert diff == {key: {"added": {}, "removed": {}, "changed": {}} for key in diff}
