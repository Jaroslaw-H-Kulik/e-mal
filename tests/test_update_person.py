"""
Layer 1 golden-master tests for POST /api/update-person.
See test_add_relationship.py for the fixture-comparison pattern.
"""
import anchors
from golden_utils import assert_matches_golden, assert_no_new_invariant_issues, state_diff


def _run(live_server, name, payload):
    before = live_server.get_state()
    response = live_server.post("/api/update-person", payload).json()
    after = live_server.get_state()

    assert_no_new_invariant_issues(before, after)
    assert_matches_golden(name, {"response": response, "diff": state_diff(before, after)})
    return response, before, after


def test_basic_fields_only_no_event_side_effects(live_server):
    """Plain field update (name/gender/occupation/tags/notes) with neither
    'birth_date'/'place_of_birth' nor 'death_date'/'place_of_death' keys
    present at all - update_person branches on key PRESENCE, so omitting
    them entirely means neither event-sync block runs."""
    payload = {
        "person_id": anchors.UPDATE_PERSON_NO_EVENTS,
        "first_name": "UpdatedFirst",
        "last_name": "UpdatedLast",
        "gender": "M",
        "occupation": "farmer",
        "tags": ["updated"],
        "notes": "updated notes",
    }
    response, before, after = _run(live_server, "update_person_basic_fields_no_events", payload)
    assert response["success"] is True
    assert response["updated_events"] == []
    assert response["person"]["first_name"] == "UpdatedFirst"
    assert after["events"] == before["events"]


def test_null_place_on_person_with_existing_events_still_marks_them_updated(live_server):
    """Real, non-obvious quirk: the real UI form (savePersonEdit in
    editor.js) always sends place_of_birth/place_of_death - null when the
    user leaves the field blank, never omitted. update_person's branch
    condition is `'place_of_birth' in person_data` (key presence), but the
    field mutation inside is guarded by `and person_data['place_of_birth']`
    (truthiness) - so for a person who already has birth/death events,
    sending null place values still finds the existing events and appends
    them to `updated_events`, even though nothing inside either event
    actually changes."""
    payload = {
        "person_id": anchors.UPDATE_PERSON_HAS_EVENTS,
        "place_of_birth": None,
        "place_of_death": None,
    }
    response, before, after = _run(
        live_server, "update_person_null_place_marks_events_updated", payload
    )
    assert response["success"] is True
    assert set(response["updated_events"]) == {
        anchors.UPDATE_PERSON_BIRTH_EVENT,
        anchors.UPDATE_PERSON_DEATH_EVENT,
    }
    for eid in response["updated_events"]:
        assert before["events"][eid] == after["events"][eid]


def test_creates_birth_and_death_events_when_none_exist(live_server):
    """A caller that supplies real birth_date/death_date dicts (not just
    place strings) for a person with no existing birth/death event - both
    get created fresh, each with the given date and a newly-created place."""
    payload = {
        "person_id": anchors.UPDATE_PERSON_NO_EVENTS,
        "birth_date": {"year": 1852, "month": None, "day": None, "circa": True},
        "place_of_birth": "UpdatePersonTestBirthPlace",
        "death_date": {"year": 1930, "month": None, "day": None, "circa": True},
        "place_of_death": "UpdatePersonTestDeathPlace",
    }
    response, before, after = _run(live_server, "update_person_creates_new_events", payload)
    assert response["success"] is True
    assert len(response["updated_events"]) == 2
    assert len(after["places"]) == len(before["places"]) + 2


def test_syncs_date_and_place_into_existing_events(live_server):
    """Person already has both a birth and a death event - supplying new
    birth_date/death_date/place_* updates them in place rather than
    creating duplicates. Both places resolve to the same existing place
    (name-only match)."""
    payload = {
        "person_id": anchors.UPDATE_PERSON_HAS_EVENTS,
        "birth_date": {"year": 1799, "month": 6, "day": 1, "circa": False},
        "place_of_birth": anchors.EXISTING_PLACE_NAME,
        "death_date": {"year": 1870, "month": None, "day": None, "circa": True},
        "place_of_death": anchors.EXISTING_PLACE_NAME,
    }
    response, before, after = _run(live_server, "update_person_syncs_existing_events", payload)
    assert response["success"] is True
    assert set(response["updated_events"]) == {
        anchors.UPDATE_PERSON_BIRTH_EVENT,
        anchors.UPDATE_PERSON_DEATH_EVENT,
    }
    assert len(after["events"]) == len(before["events"])  # no new events
    assert after["events"][anchors.UPDATE_PERSON_BIRTH_EVENT]["date"]["year"] == 1799
    assert after["events"][anchors.UPDATE_PERSON_DEATH_EVENT]["date"]["year"] == 1870
    assert after["events"][anchors.UPDATE_PERSON_BIRTH_EVENT]["place_id"] == "PL0001"


def test_nonexistent_person_fails_cleanly(live_server):
    payload = {"person_id": anchors.NONEXISTENT_PERSON_ID, "first_name": "X"}
    before = live_server.get_state()
    response = live_server.post("/api/update-person", payload).json()
    after = live_server.get_state()

    assert response == {"success": False, "error": "Person not found"}
    diff = state_diff(before, after)
    assert diff == {key: {"added": {}, "removed": {}, "changed": {}} for key in diff}
