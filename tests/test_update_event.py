"""
Layer 1 golden-master tests for POST /api/update-event.
See test_add_relationship.py for the fixture-comparison pattern.
"""
import anchors
from golden_utils import assert_matches_golden, assert_no_new_invariant_issues, state_diff


def _run(live_server, name, payload, extra_new_id_diffs=None):
    before = live_server.get_state()
    response = live_server.post("/api/update-event", payload).json()
    after = live_server.get_state()

    assert_no_new_invariant_issues(before, after)
    assert_matches_golden(
        name, {"response": response, "diff": state_diff(before, after)}, extra_new_id_diffs
    )
    return response, before, after


def test_swap_participants_on_existing_event(live_server):
    """update_event fully replaces an event's participant list rather than
    merging - this drops one witness, keeps the deceased + the other
    witness, and adds a new witness. place_name/house_number are pinned to
    the event's real place (PL0040) since update_event has no "leave place
    alone" path: omitting place_name unconditionally resets place_id to
    None, which would pollute this diff with an unrelated change."""
    payload = {
        "event_id": anchors.SWAP_EVENT,
        "type": "death",
        "date": {"year": 1831, "month": 2, "day": 7},
        "place_name": anchors.SWAP_EVENT_PLACE_NAME,
        "house_number": anchors.SWAP_EVENT_PLACE_HOUSE_NUMBER,
        "notes": "Source line: 46",
        "tags": [],
        "links": [
            "https://www.familysearch.org/ark:/61903/3:1:939V-T69C-NG?cc=1407440&lang=en&i=187"
        ],
        "participants": [
            {"existing_person_id": anchors.SWAP_KEEP_DECEASED, "role": "deceased"},
            {"existing_person_id": anchors.SWAP_KEEP_WITNESS, "role": "witness"},
            {"existing_person_id": anchors.SWAP_NEW_WITNESS, "role": "witness"},
        ],
    }
    response, before, after = _run(live_server, "update_event_swap_participants", payload)
    assert response["success"] is True
    old_participant_ids = {
        ep["person_id"] for ep in before["event_participations"].values()
        if ep["event_id"] == anchors.SWAP_EVENT
    }
    new_participant_ids = {
        ep["person_id"] for ep in after["event_participations"].values()
        if ep["event_id"] == anchors.SWAP_EVENT
    }
    assert anchors.SWAP_DROP_WITNESS in old_participant_ids
    assert anchors.SWAP_DROP_WITNESS not in new_participant_ids
    assert anchors.SWAP_NEW_WITNESS in new_participant_ids


def test_new_child_and_parents_on_existing_birth_event(live_server):
    """Same shape of input as test_add_event.py's
    test_birth_with_brand_new_child_and_new_parents, run through
    update_event instead of add_event, on E1746 (an existing birth event).

    update_event previously had no is_child_in_birth_event check (unlike
    add_event), so it unconditionally created a *second*, duplicate birth
    event for the new child even though E1746 itself already served as
    their birth event - a real multiple_birth_events invariant violation.
    Fixed by porting add_event's three-way branch
    (is_child_in_birth_event / existing_birth_event_id / else) into
    update_event. This test now pins the corrected behavior: only the
    auto-marriage event between the two new parents is created, no
    duplicate birth event - and the new parents are now linked to E1746
    itself as father/mother participants (same fix as add_event's
    equivalent scenario - see test_add_event.py).
    """
    payload = {
        "event_id": anchors.UPDATE_NEW_CHILD_EVENT,
        "type": "birth",
        "date": {"year": 1802, "month": None, "day": None, "circa": True},
        "notes": "Migrated from person model (step 56.1)",
        "tags": [],
        "links": [],
        "participants": [
            {
                "first_name": "TestChild2",
                "last_name": "Fixture",
                "role": "child",
                "parent_mother": {"first_name": "TestMother2", "last_name": "Fixture"},
                "parent_father": {"first_name": "TestFather2", "last_name": "Fixture"},
            }
        ],
    }
    response, before, after = _run(live_server, "update_event_new_child_new_parents", payload)
    assert response["success"] is True
    assert len(response["new_persons"]) == 3  # child, mother, father
    # No more duplicate birth event - only the auto-marriage event is new.
    assert len(after["events"]) == len(before["events"]) + 1
    linked_roles = {
        ep["role"] for ep in after["event_participations"].values()
        if ep["event_id"] == anchors.UPDATE_NEW_CHILD_EVENT
    }
    assert linked_roles == {"child", "mother", "father"}
    # Same still-open content-string gap as add_event's equivalent scenario.
    assert response["event"]["content"] == "child: TestChild2 Fixture"


def test_swap_participants_and_new_child_combined(live_server):
    """Combines two things in one update_event call: pre-existing unrelated
    participants (witnesses) that must survive the full participant-list
    replace, and a brand-new child+parents that must get linked via the
    is_child_in_birth_event fix - checking the two code paths don't step on
    each other's EP id allocation (event_participations' ids are all
    max(existing)+1 recomputed inline, not a counter).

    Setup: first add a birth event with a placeholder existing child plus
    two witnesses (not itself asserted against a fixture - just gets a
    known event_id to update). Then update it, replacing the child with a
    new one (new parents included) while keeping both witnesses.

    The setup call's own ids (the event and its 3 participations) are real,
    live-dataset-derived ids too, and would otherwise drift the fixture the
    same way the diffed call's ids would - so its before/after is diffed
    and passed to assert_matches_golden purely to get those ids normalized,
    even though that diff isn't itself part of what's persisted.
    """
    pre_setup_state = live_server.get_state()
    setup_payload = {
        "type": "birth",
        "date": {"year": 1884, "month": None, "day": None},
        "notes": "Layer 1 golden-master test fixture (setup)",
        "participants": [
            {"existing_person_id": anchors.COMBINED_SETUP_CHILD, "role": "child"},
            {"existing_person_id": anchors.COMBINED_WITNESS_1, "role": "witness"},
            {"existing_person_id": anchors.COMBINED_WITNESS_2, "role": "witness"},
        ],
    }
    setup_response = live_server.post("/api/add-event", setup_payload).json()
    assert setup_response["success"] is True
    target_event_id = setup_response["event"]["id"]
    setup_diff = state_diff(pre_setup_state, live_server.get_state())

    update_payload = {
        "event_id": target_event_id,
        "type": "birth",
        "date": {"year": 1884, "month": None, "day": None},
        "notes": "Layer 1 golden-master test fixture (setup)",
        "tags": [],
        "links": [],
        "participants": [
            {"existing_person_id": anchors.COMBINED_WITNESS_1, "role": "witness"},
            {"existing_person_id": anchors.COMBINED_WITNESS_2, "role": "witness"},
            {
                "first_name": "TestChild7",
                "last_name": "Fixture",
                "role": "child",
                "parent_mother": {"first_name": "TestMother7", "last_name": "Fixture"},
                "parent_father": {"first_name": "TestFather7", "last_name": "Fixture"},
            },
        ],
    }
    response, before, after = _run(
        live_server, "update_event_swap_and_new_child_combined", update_payload,
        extra_new_id_diffs=[setup_diff],
    )
    assert response["success"] is True
    assert len(response["new_persons"]) == 3  # child, mother, father

    final_participants = {
        (ep["person_id"], ep["role"]) for ep in after["event_participations"].values()
        if ep["event_id"] == target_event_id
    }
    assert (anchors.COMBINED_WITNESS_1, "witness") in final_participants
    assert (anchors.COMBINED_WITNESS_2, "witness") in final_participants
    assert (anchors.COMBINED_SETUP_CHILD, "child") not in final_participants
    roles = {role for _, role in final_participants}
    assert roles == {"witness", "child", "mother", "father"}
    # 3 old participations (setup child + 2 witnesses) removed. 7 new ones
    # added: witness1, witness2, child from the main participant loop (3);
    # mother+father linked to this event via the is_child_in_birth_event
    # fix (2); groom+bride on the auto-created marriage event between the
    # two new parents (2). Net +4. No EP id collisions: dict keys already
    # guarantee uniqueness, this just confirms neither code path silently
    # overwrote another's entry by re-using an id.
    assert len(after["event_participations"]) == len(before["event_participations"]) + 4


def test_nonexistent_event_id_fails_cleanly(live_server):
    payload = {
        "event_id": anchors.NONEXISTENT_EVENT_ID,
        "type": "generic",
        "date": None,
        "participants": [],
    }
    before = live_server.get_state()
    response = live_server.post("/api/update-event", payload).json()
    after = live_server.get_state()

    assert response == {
        "success": False,
        "error": f"Event {anchors.NONEXISTENT_EVENT_ID} not found",
    }
    diff = state_diff(before, after)
    assert diff == {key: {"added": {}, "removed": {}, "changed": {}} for key in diff}
