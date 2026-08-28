"""
Layer 1 golden-master tests for POST /api/add-person.
See test_add_relationship.py for the fixture-comparison pattern.
"""
import anchors
from golden_utils import assert_matches_golden, assert_no_new_invariant_issues, state_diff


def _run(live_server, name, payload):
    before = live_server.get_state()
    response = live_server.post("/api/add-person", payload).json()
    after = live_server.get_state()

    assert_no_new_invariant_issues(before, after)
    assert_matches_golden(name, {"response": response, "diff": state_diff(before, after)})
    return response, before, after


def test_minimal_person_gets_auto_birth_event_only(live_server):
    """Step 9: every add-person call ALWAYS creates a birth event, even with
    no birth data at all (date=None, place_id=None) - and never a death
    event unless death data is supplied. Note the birth event created here
    has no 'content' key at all (only 'description') - a different event
    shape than add_event/update_event produce, which always set 'content'."""
    payload = {
        "given_name": "TestMinimal",
        "surname": "Fixture",
        "gender": "M",
    }
    response, before, after = _run(live_server, "add_person_minimal", payload)
    assert response["success"] is True
    assert len(response["created_events"]) == 1
    birth_event = after["events"][response["created_events"][0]]
    assert birth_event["type"] == "birth"
    assert birth_event["date"] is None
    assert birth_event["place_id"] is None
    assert response["person"]["occupation"] is None
    assert response["person"]["tags"] == []
    assert response["person"]["notes"] is None


def test_full_person_creates_birth_and_death_events_with_places(live_server):
    """given_name/surname (not first_name/last_name) + birth_year_estimate/
    death_year_estimate (not *_date dicts) is the shape the real Add Person
    form actually sends (web/index.html add-person-form) - year estimates
    become circa dates. place_of_birth matches an existing place by name
    only (house_number is NOT part of the match here - find_or_create_place
    ignores it, unlike add_event's handle_place); place_of_death is new."""
    payload = {
        "given_name": "TestFull",
        "surname": "Fixture",
        "maiden_name": "MaidenFixture",
        "gender": "F",
        "occupation": "seamstress",
        "tags": ["test"],
        "notes": "fixture notes",
        "birth_year_estimate": 1850,
        "death_year_estimate": 1920,
        "place_of_birth": anchors.EXISTING_PLACE_NAME,
        "place_of_death": "Nowa Wies AddPersonTestOnly",
    }
    response, before, after = _run(live_server, "add_person_full_with_places", payload)
    assert response["success"] is True
    assert len(response["created_events"]) == 2
    types = {after["events"][eid]["type"] for eid in response["created_events"]}
    assert types == {"birth", "death"}
    # place_of_birth reused an existing place (name-only match); place_of_death created a new one.
    assert len(after["places"]) == len(before["places"]) + 1
    birth_event = next(
        after["events"][eid] for eid in response["created_events"]
        if after["events"][eid]["type"] == "birth"
    )
    assert birth_event["date"] == {"year": 1850, "month": None, "day": None, "circa": True}
    assert birth_event["place_id"] == "PL0001"


def test_first_name_last_name_and_full_date_dicts_also_accepted(live_server):
    """A different real call site (the GEDCOM-import add-person flow in
    editor.js) sends first_name/last_name and a full birth_date dict
    instead of given_name/surname + birth_year_estimate - both shapes are
    accepted via the `.get('given_name', .get('first_name', ''))` fallback
    chain."""
    payload = {
        "first_name": "TestAlt",
        "last_name": "Fixture",
        "gender": "M",
        "birth_date": {"year": 1875, "month": 3, "day": 12, "circa": False},
    }
    response, before, after = _run(live_server, "add_person_first_last_name_shape", payload)
    assert response["success"] is True
    assert response["person"]["first_name"] == "TestAlt"
    assert response["person"]["last_name"] == "Fixture"
    birth_event = after["events"][response["created_events"][0]]
    assert birth_event["date"] == {"year": 1875, "month": 3, "day": 12, "circa": False}
