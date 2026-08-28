"""
Layer 1 golden-master tests for POST /api/add-event.
See test_add_relationship.py for the fixture-comparison pattern.
"""
import anchors
from golden_utils import assert_matches_golden, assert_no_new_invariant_issues, state_diff


def _run(live_server, name, payload):
    before = live_server.get_state()
    response = live_server.post("/api/add-event", payload).json()
    after = live_server.get_state()

    assert_no_new_invariant_issues(before, after)
    assert_matches_golden(name, {"response": response, "diff": state_diff(before, after)})
    return response, before, after


def test_plain_birth_all_existing_participants(live_server):
    """Baseline create path: existing persons only, parents already married
    via another event so create_parent_marriage_if_needed is a no-op - no
    cascades, just the new event + 3 participations."""
    payload = {
        "type": "birth",
        "date": {"year": 1850, "month": None, "day": None},
        "notes": "Layer 1 golden-master test fixture",
        "participants": [
            {"existing_person_id": anchors.PLAIN_BIRTH_CHILD, "role": "child"},
            {"existing_person_id": anchors.PLAIN_BIRTH_FATHER, "role": "father"},
            {"existing_person_id": anchors.PLAIN_BIRTH_MOTHER, "role": "mother"},
        ],
    }
    response, _, _ = _run(live_server, "add_event_plain_birth_existing_participants", payload)
    assert response["success"] is True
    assert response["new_persons"] == []


def test_birth_with_brand_new_child_and_new_parents(live_server):
    """New child (role='child') in a 'birth' event, with new parent_mother/
    parent_father supplied inline.

    is_child_in_birth_event is True here, so add_event deliberately does
    NOT create a second, separate birth event for the child (the event
    being added already IS their birth event). The new mother/father are
    now also linked to *this* birth event as father/mother participants
    (previously they were only created as Person records and married to
    each other via an auto-marriage event, never attached to the birth
    event itself - fixed in server.py's is_child_in_birth_event branch).

    Still open: the event's auto-generated `content` string is built only
    from event_data['participants'] entries, and the parents are nested
    under the child's parent_mother/parent_father keys rather than being
    separate participant entries - so content still reads just
    "child: TestChild Fixture" even though father/mother are now properly
    linked in event_participations. Cosmetic, not corrected here.
    """
    payload = {
        "type": "birth",
        "date": {"year": 1880, "month": 5, "day": 1},
        "notes": "Layer 1 golden-master test fixture",
        "participants": [
            {
                "first_name": "TestChild",
                "last_name": "Fixture",
                "role": "child",
                "parent_mother": {"first_name": "TestMother", "last_name": "Fixture"},
                "parent_father": {"first_name": "TestFather", "last_name": "Fixture"},
            }
        ],
    }
    response, before, after = _run(live_server, "add_event_birth_new_child_new_parents", payload)
    assert response["success"] is True
    assert len(response["new_persons"]) == 3  # child, mother, father
    new_event_id = response["event"]["id"]
    linked_roles = {
        ep["role"] for ep in after["event_participations"].values()
        if ep["event_id"] == new_event_id
    }
    assert linked_roles == {"child", "mother", "father"}
    # Pins the still-open content-string gap noted above: parents are
    # linked as participants but never make it into the auto-generated
    # content text.
    assert response["event"]["content"] == "child: TestChild Fixture"


def test_new_child_mixed_new_and_existing_parent(live_server):
    """parent_mother is new, parent_father uses existing_person_id. Both
    should end up linked to the new birth event; only the mother counts as
    a newly-created person.

    Note: parent_father must carry first_name/last_name here even though
    it also carries existing_person_id - see
    test_existing_parent_without_name_fields_is_silently_dropped below for
    what happens without them (the real UI presumably always sends both,
    so this matches actual usage)."""
    payload = {
        "type": "birth",
        "date": {"year": 1881, "month": None, "day": None},
        "notes": "Layer 1 golden-master test fixture",
        "participants": [
            {
                "first_name": "TestChild4",
                "last_name": "Fixture",
                "role": "child",
                "parent_mother": {"first_name": "TestMother4", "last_name": "Fixture"},
                "parent_father": {
                    "existing_person_id": anchors.MIXED_PARENT_EXISTING_FATHER,
                    "first_name": "Bernard",
                    "last_name": "Borowiec",
                },
            }
        ],
    }
    response, before, after = _run(live_server, "add_event_new_child_mixed_parent", payload)
    assert response["success"] is True
    assert len(response["new_persons"]) == 2  # child, mother (father is existing)
    new_event_id = response["event"]["id"]
    linked = {
        (ep["person_id"], ep["role"]) for ep in after["event_participations"].values()
        if ep["event_id"] == new_event_id
    }
    assert (anchors.MIXED_PARENT_EXISTING_FATHER, "father") in linked


def test_new_child_conflicting_father_not_deduplicated(live_server):
    """An existing person already holds 'father' as their own top-level
    participant entry, while the new child's parent_father creates a
    *different*, brand-new father. The is_child_in_birth_event fix only
    checks "is this exact person already linked", not "is this role slot
    already taken by someone else" - so both end up linked as 'father' on
    the same event. Documents current behavior (not corrected here);
    contrast with sync_parents_to_birth_events (test_sync_parents_...
    below), which does guard against this via its `existing_parent` check.
    """
    payload = {
        "type": "birth",
        "date": {"year": 1882, "month": None, "day": None},
        "notes": "Layer 1 golden-master test fixture",
        "participants": [
            {"existing_person_id": anchors.CONFLICTING_FATHER, "role": "father"},
            {
                "first_name": "TestChild5",
                "last_name": "Fixture",
                "role": "child",
                "parent_father": {"first_name": "TestFather5", "last_name": "Fixture"},
            },
        ],
    }
    response, before, after = _run(live_server, "add_event_new_child_conflicting_father", payload)
    assert response["success"] is True
    new_event_id = response["event"]["id"]
    fathers = [
        ep["person_id"] for ep in after["event_participations"].values()
        if ep["event_id"] == new_event_id and ep["role"] == "father"
    ]
    assert len(fathers) == 2
    assert anchors.CONFLICTING_FATHER in fathers


def test_new_child_both_parents_already_existing(live_server):
    """parent_mother and parent_father both use existing_person_id, plus
    their real first_name/last_name (required - see the dedicated gotcha
    test below) - only the child is a new person; both existing parents
    get linked to the new birth event, and a marriage event is still
    auto-created between them since the code doesn't check whether they're
    already married to each other before creating one (a separate,
    narrower version of the same "no existing-marriage check" pattern
    already covered for add_relationship's spouse branch - here, unlike
    that branch, there's no find_marriage_event_between guard at all)."""
    payload = {
        "type": "birth",
        "date": {"year": 1883, "month": None, "day": None},
        "notes": "Layer 1 golden-master test fixture",
        "participants": [
            {
                "first_name": "TestChild6",
                "last_name": "Fixture",
                "role": "child",
                "parent_mother": {
                    "existing_person_id": anchors.UNRELATED_FEMALE,
                    "first_name": "Marianna",
                    "last_name": "Jarosz",
                },
                "parent_father": {
                    "existing_person_id": anchors.UNRELATED_MALE,
                    "first_name": "Bernard",
                    "last_name": "Borowiec",
                },
            }
        ],
    }
    response, before, after = _run(live_server, "add_event_new_child_both_parents_existing", payload)
    assert response["success"] is True
    assert len(response["new_persons"]) == 1  # child only
    new_event_id = response["event"]["id"]
    linked = {
        (ep["person_id"], ep["role"]) for ep in after["event_participations"].values()
        if ep["event_id"] == new_event_id
    }
    assert (anchors.UNRELATED_FEMALE, "mother") in linked
    assert (anchors.UNRELATED_MALE, "father") in linked
    # Auto-marriage still created, unconditionally:
    new_marriage_events = [e for e in after["events"] if e not in before["events"]]
    assert any(after["events"][eid]["type"] == "marriage" for eid in new_marriage_events)


def test_existing_parent_without_name_fields_is_silently_dropped(live_server):
    """A real, non-obvious gotcha: parent_mother/parent_father are only
    processed at all if first_name AND last_name are present -
    `if parent_data and parent_data.get('first_name') and
    parent_data.get('last_name')` gates the whole block, including the
    existing_person_id lookup. Supplying only existing_person_id (no
    names) means the parent is silently ignored: no person created, no
    error, no participation added - as if parent_mother/parent_father had
    been omitted entirely. Not fixed here (the real UI form presumably
    always populates name fields alongside an existing-person selection,
    so this may never trigger in practice) - pinned so a future caller
    that omits names doesn't get silently dropped data without warning."""
    payload = {
        "type": "birth",
        "date": {"year": 1885, "month": None, "day": None},
        "notes": "Layer 1 golden-master test fixture",
        "participants": [
            {
                "first_name": "TestChild8",
                "last_name": "Fixture",
                "role": "child",
                "parent_mother": {"existing_person_id": anchors.UNRELATED_FEMALE},
            }
        ],
    }
    response, before, after = _run(live_server, "add_event_existing_parent_without_names_dropped", payload)
    assert response["success"] is True
    assert len(response["new_persons"]) == 1  # child only - mother silently never processed
    new_event_id = response["event"]["id"]
    linked = {
        (ep["person_id"], ep["role"]) for ep in after["event_participations"].values()
        if ep["event_id"] == new_event_id
    }
    assert linked == {(response["new_persons"][0]["id"], "child")}
    assert anchors.UNRELATED_FEMALE not in {pid for pid, _ in linked}


def test_sync_parents_to_birth_events_via_role_suffix(live_server):
    """sync_parents_to_birth_events is a separate, older mechanism from the
    is_child_in_birth_event fix above: a participant's own parent is
    supplied as a second top-level participant with role
    '<main_role>_parent_<father|mother>' (e.g. 'groom_parent_father'), and
    both sides must use existing_person_id (no new-person creation here).

    Groom has no existing birth event, so this auto-creates one for him
    with the given father attached - showing this mechanism correctly
    links the parent (unlike the bug fixed above, it already had no gap
    here, since it explicitly checks for + skips an existing different
    parent rather than double-adding)."""
    payload = {
        "type": "marriage",
        "date": {"year": 1850, "month": None, "day": None},
        "notes": "Layer 1 golden-master test fixture",
        "participants": [
            {"existing_person_id": anchors.SYNC_GROOM, "role": "groom"},
            {"existing_person_id": anchors.SYNC_BRIDE, "role": "bride"},
            {"existing_person_id": anchors.SYNC_GROOM_FATHER, "role": "groom_parent_father"},
        ],
    }
    response, before, after = _run(live_server, "add_event_sync_parents_role_suffix", payload)
    assert response["success"] is True
    birth_events = [
        eid for eid in after["events"]
        if eid not in before["events"] and after["events"][eid]["type"] == "birth"
    ]
    assert len(birth_events) == 1
    linked = {
        (ep["person_id"], ep["role"]) for ep in after["event_participations"].values()
        if ep["event_id"] == birth_events[0]
    }
    assert (anchors.SYNC_GROOM, "child") in linked
    assert (anchors.SYNC_GROOM_FATHER, "father") in linked


def test_plain_marriage_event(live_server):
    payload = {
        "type": "marriage",
        "date": {"year": 1850, "month": None, "day": None},
        "notes": "Layer 1 golden-master test fixture",
        "participants": [
            {"existing_person_id": anchors.PLAIN_MARRIAGE_GROOM, "role": "groom"},
            {"existing_person_id": anchors.PLAIN_MARRIAGE_BRIDE, "role": "bride"},
        ],
    }
    response, _, _ = _run(live_server, "add_event_plain_marriage", payload)
    assert response["success"] is True


def test_plain_death_event(live_server):
    payload = {
        "type": "death",
        "date": {"year": 1850, "month": None, "day": None},
        "notes": "Layer 1 golden-master test fixture",
        "participants": [
            {"existing_person_id": anchors.PLAIN_DEATH_DECEASED, "role": "deceased"},
        ],
    }
    response, _, _ = _run(live_server, "add_event_plain_death", payload)
    assert response["success"] is True


def test_plain_generic_event(live_server):
    payload = {
        "type": "generic",
        "date": {"year": 1850, "month": None, "day": None},
        "notes": "Layer 1 golden-master test fixture",
        "participants": [
            {"existing_person_id": anchors.PLAIN_GENERIC_PARTICIPANT, "role": "participant"},
        ],
    }
    response, _, _ = _run(live_server, "add_event_plain_generic", payload)
    assert response["success"] is True


def test_creates_new_place(live_server):
    payload = {
        "type": "generic",
        "date": {"year": 1850, "month": None, "day": None},
        "place_name": anchors.NEW_PLACE_NAME,
        "house_number": anchors.NEW_PLACE_HOUSE_NUMBER,
        "notes": "Layer 1 golden-master test fixture",
        # A non-empty participant list avoids tripping the (pre-existing,
        # legitimate) orphan_event invariant warning - this test is about
        # place resolution, not participant handling.
        "participants": [
            {"existing_person_id": anchors.PLAIN_GENERIC_PARTICIPANT, "role": "participant"},
        ],
    }
    response, before, after = _run(live_server, "add_event_creates_new_place", payload)
    assert response["success"] is True
    assert len(after["places"]) == len(before["places"]) + 1


def test_reuses_existing_place(live_server):
    """place_name + house_number matching an existing place (PL0001) should
    resolve to it rather than creating a duplicate."""
    payload = {
        "type": "generic",
        "date": {"year": 1850, "month": None, "day": None},
        "place_name": anchors.EXISTING_PLACE_NAME,
        "house_number": anchors.EXISTING_PLACE_HOUSE_NUMBER,
        "notes": "Layer 1 golden-master test fixture",
        "participants": [
            {"existing_person_id": anchors.PLAIN_GENERIC_PARTICIPANT, "role": "participant"},
        ],
    }
    response, before, after = _run(live_server, "add_event_reuses_existing_place", payload)
    assert response["success"] is True
    assert len(after["places"]) == len(before["places"])
