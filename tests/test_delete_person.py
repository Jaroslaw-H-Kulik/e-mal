"""
Layer 1 golden-master tests for POST /api/delete-person.
See test_add_relationship.py for the fixture-comparison pattern.
"""
from collections import Counter

import anchors
from golden_utils import assert_matches_golden, state_diff
from invariants import run_all_checks


def test_cascades_empty_events_but_leaves_marriages_short_a_groom(live_server):
    """P0011 participates in 7 events. E0004 (death/deceased) and E0653
    (birth/child) are events where P0011 is the SOLE participant - those
    get deleted entirely once the participation is removed. E0555
    (death/witness), E0651 (birth/witness) and E0776 (birth/father) have
    other participants and survive completely untouched (witness/father
    aren't cardinality-checked roles for their event types).

    E1415 and E1416 (marriage/groom) also have another participant (the
    bride) and survive - but delete_person has no guard against removing a
    cardinality-required role: both marriages now have zero grooms, a
    real, currently-unhandled data-integrity gap. This is deliberately
    checked directly against invariants.run_all_checks (rather than the
    usual assert_no_new_invariant_issues helper) so the regression is
    pinned as expected, documented behavior instead of silently failing
    the test.

    family_relationships isn't a key in the live data at all (see
    TESTING_STRATEGY.md), so deleted_relationships is always 0 here - dead
    code for this dataset, not a bug.
    """
    payload = {"person_id": anchors.DELETE_PERSON_ID}
    before = live_server.get_state()
    response = live_server.post("/api/delete-person", payload).json()
    after = live_server.get_state()

    assert_matches_golden(
        "delete_person_cascade_and_preserve",
        {"response": response, "diff": state_diff(before, after)},
    )

    assert response["success"] is True
    assert response["deleted_relationships"] == 0
    assert anchors.DELETE_PERSON_ID not in after["persons"]
    assert set(response["deleted_events"]) == {"E0004", "E0653"}

    for eid in ("E0555", "E0651", "E0776"):
        assert eid in after["events"]
        assert before["events"][eid] == after["events"][eid]
        remaining = [ep for ep in after["event_participations"].values() if ep["event_id"] == eid]
        assert all(ep["person_id"] != anchors.DELETE_PERSON_ID for ep in remaining)

    for eid in ("E1415", "E1416"):
        assert eid in after["events"]
        remaining_roles = {
            ep["role"] for ep in after["event_participations"].values() if ep["event_id"] == eid
        }
        assert "groom" not in remaining_roles

    before_counts = Counter(issue.code for issue in run_all_checks(before))
    after_counts = Counter(issue.code for issue in run_all_checks(after))
    assert after_counts["role_cardinality"] == before_counts["role_cardinality"] + 2


def test_nonexistent_person_fails_cleanly(live_server):
    payload = {"person_id": anchors.NONEXISTENT_PERSON_ID}
    before = live_server.get_state()
    response = live_server.post("/api/delete-person", payload).json()
    after = live_server.get_state()

    assert response == {"success": False, "error": "Person not found"}
    diff = state_diff(before, after)
    assert diff == {key: {"added": {}, "removed": {}, "changed": {}} for key in diff}
