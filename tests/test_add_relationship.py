"""
Layer 1 golden-master tests for POST /api/add-relationship.

Each test: capture state before, POST, capture state after, diff, and
assert the (response, diff) pair matches a committed fixture under
tests/golden/. First run per fixture name writes the file and fails on
purpose - see golden_utils.assert_matches_golden.
"""
import anchors
from golden_utils import assert_matches_golden, assert_no_new_invariant_issues, state_diff


def _run(live_server, name, payload):
    before = live_server.get_state()
    response = live_server.post("/api/add-relationship", payload).json()
    after = live_server.get_state()

    assert_no_new_invariant_issues(before, after)
    assert_matches_golden(name, {"response": response, "diff": state_diff(before, after)})
    return response, before, after


def test_parent_creates_birth_event_when_none_exists(live_server):
    """Base person has no birth event yet -> a new one is created for them,
    with the target person attached as the given parent role."""
    payload = {
        "base_person_id": anchors.NO_BIRTH_EVENT_CHILD,
        "target_person_id": anchors.UNRELATED_FEMALE,
        "relationship_type": "parent",
        "role": "mother",
    }
    response, _, _ = _run(live_server, "add_relationship_parent_new_birth_event", payload)
    assert response["success"] is True
    assert response["created_event"] is not None
    assert response["updated_event"] is None


def test_parent_reuses_existing_birth_event(live_server):
    """Base person already has a birth event -> it's updated in place
    (target added as the given parent role), no second birth event created."""
    payload = {
        "base_person_id": anchors.HAS_BIRTH_EVENT_CHILD,
        "target_person_id": anchors.UNRELATED_MALE,
        "relationship_type": "parent",
        "role": "father",
    }
    response, _, _ = _run(live_server, "add_relationship_parent_reuses_birth_event", payload)
    assert response["success"] is True
    assert response["created_event"] is None
    assert response["updated_event"] == anchors.HAS_BIRTH_EVENT_CHILD_EVENT


def test_spouse_creates_marriage_event(live_server):
    """No marriage event exists between this specific pair (even though
    the base person is already married to someone else) -> a new marriage
    event is created with gender-derived groom/bride roles."""
    payload = {
        "base_person_id": anchors.SPOUSE_BASE,
        "target_person_id": anchors.SPOUSE_TARGET,
        "relationship_type": "spouse",
        "role": "spouse",
    }
    response, _, _ = _run(live_server, "add_relationship_spouse_new_marriage_event", payload)
    assert response["success"] is True
    assert response["created_event"] is not None
    assert response["updated_event"] is None


def test_godparent_reuses_existing_birth_event(live_server):
    """Target is added as godparent to the base person's existing birth
    event."""
    payload = {
        "base_person_id": anchors.GODPARENT_CHILD,
        "target_person_id": anchors.NEW_GODPARENT,
        "relationship_type": "godparent",
        "role": "godparent",
    }
    response, _, _ = _run(live_server, "add_relationship_godparent_reuses_birth_event", payload)
    assert response["success"] is True
    assert response["created_event"] is None
    assert response["updated_event"] == anchors.GODPARENT_CHILD_EVENT


def test_missing_role_key_fails_cleanly(live_server):
    """rel_data['role'] is read unconditionally before the type dispatch -
    a missing key raises inside the handler's own try/except and comes back
    as a normal {'success': False} response, with no partial write."""
    payload = {
        "base_person_id": anchors.NO_BIRTH_EVENT_CHILD,
        "target_person_id": anchors.UNRELATED_FEMALE,
        "relationship_type": "parent",
        # 'role' intentionally omitted
    }
    before = live_server.get_state()
    response = live_server.post("/api/add-relationship", payload).json()
    after = live_server.get_state()

    assert response == {"success": False, "error": "'role'"}
    diff = state_diff(before, after)
    assert diff == {key: {"added": {}, "removed": {}, "changed": {}} for key in diff}


def test_unknown_relationship_type_fails_cleanly(live_server):
    """An unrecognized relationship_type hits the handler's own explicit
    else-branch (not an exception) - still a clean {'success': False}, no
    state change."""
    payload = {
        "base_person_id": anchors.NO_BIRTH_EVENT_CHILD,
        "target_person_id": anchors.UNRELATED_FEMALE,
        "relationship_type": "sibling",
        "role": "sibling",
    }
    before = live_server.get_state()
    response = live_server.post("/api/add-relationship", payload).json()
    after = live_server.get_state()

    assert response == {
        "success": False,
        "error": "Unknown relationship type: sibling",
    }
    diff = state_diff(before, after)
    assert diff == {key: {"added": {}, "removed": {}, "changed": {}} for key in diff}
