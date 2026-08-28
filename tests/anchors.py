"""
Fixed reference IDs from the real dataset, picked once for Layer 1
golden-master scenarios so payloads use real, meaningful people/events
instead of synthetic ones. Each `live_server` test gets its own sandboxed
copy of the data (see conftest.py) - reusing the same ID across scenarios
in different test functions is safe, they never share state.

If the real dataset is regenerated/edited and one of these IDs stops
resolving to the same record, the affected golden-master test will fail
loudly (KeyError from the server, or a fixture mismatch) rather than
silently testing the wrong thing - that's intentional, not a maintenance
bug to route around.
"""

# --- add_relationship: parent, no existing birth event ---------------------
# P0012 Ignacy Raczynski (M) has no birth event on file.
NO_BIRTH_EVENT_CHILD = "P0012"
# P0033 Marianna Jarosz (F), otherwise unconnected to P0012 - added as mother.
UNRELATED_FEMALE = "P0033"

# --- add_relationship: parent, existing birth event gets reused ------------
# P0800 Karol Strzembosz (M) already has birth event E1746, currently with
# only 'child' present (no parents yet) - relationship-add should update
# E1746 in place rather than creating a second birth event for P0800.
HAS_BIRTH_EVENT_CHILD = "P0800"
HAS_BIRTH_EVENT_CHILD_EVENT = "E1746"
# P0038 Bernard Borowiec (M), unconnected - added as father.
UNRELATED_MALE = "P0038"

# --- add_relationship: spouse, no marriage between this specific pair ------
# P0001 Jan Surdey (M) is already married to P0002 (event E0400), but never
# to P0007 Marianna Surdey (F) - exercises find_marriage_event_between being
# pair-specific ("married to *this* person"), not "already has any spouse".
SPOUSE_BASE = "P0001"
SPOUSE_TARGET = "P0007"

# --- add_relationship: godparent, existing birth event, 0 godparents so far
# P0114 Wincenty Surdey (M) has birth event E0583 (father P0006, mother
# P0020, no godparents yet).
GODPARENT_CHILD = "P0114"
GODPARENT_CHILD_EVENT = "E0583"
NEW_GODPARENT = "P0042"  # Karol Stumborz (M), unconnected

# --- add_event: plain birth, all-existing participants ---------------------
# Parents P0001/P0002 are already married via E0400, so
# create_parent_marriage_if_needed is a clean no-op here (no auto-marriage
# noise in the diff) - isolates the "plain create" path.
PLAIN_BIRTH_CHILD = "P0012"   # reused id, unrelated test/sandbox
PLAIN_BIRTH_FATHER = "P0001"  # Jan Surdey
PLAIN_BIRTH_MOTHER = "P0002"  # Helena Surdey

# --- add_event: plain marriage / death / generic, no cascades --------------
PLAIN_MARRIAGE_GROOM = "P0009"       # Antoni Lapacz (M), unmarried
PLAIN_MARRIAGE_BRIDE = "P0021"       # Franciszka Surdey (F), unmarried
PLAIN_DEATH_DECEASED = "P0012"       # Ignacy Raczynski, no existing death event
PLAIN_GENERIC_PARTICIPANT = "P0033"  # Marianna Jarosz

# --- add_event: place reuse vs create ---------------------------------------
EXISTING_PLACE_NAME = "Małyszyn"  # matches PL0001
EXISTING_PLACE_HOUSE_NUMBER = "16"
NEW_PLACE_NAME = "Nowa Wies TestOnly"
NEW_PLACE_HOUSE_NUMBER = "5"

# --- update_event: swap participants on a small non-birth event ------------
# E0013 death event: deceased P0020, witnesses P0015 + P0632. Test keeps
# deceased + one witness, drops the other, adds a new one. place_name/
# house_number pinned to PL0040's actual values so the payload doesn't
# accidentally clear event['place_id'] (update_event has no "keep existing
# place" path - omitting place_name always resets it to None).
SWAP_EVENT = "E0013"
SWAP_EVENT_PLACE_NAME = "Małyszyn"  # matches PL0040
SWAP_EVENT_PLACE_HOUSE_NUMBER = "21"
SWAP_KEEP_DECEASED = "P0020"
SWAP_KEEP_WITNESS = "P0015"
SWAP_DROP_WITNESS = "P0632"
SWAP_NEW_WITNESS = "P0022"  # Piotr Kleczaj (M), unconnected

# --- update_event: new child+parents on an existing birth event ------------
# Same shape of input as the add_event new-child scenario, run through
# update_event instead - see test docstring for the behavioral discrepancy
# this is designed to expose (update_event has no "this IS the birth event"
# skip that add_event has, so it creates a second, duplicate birth event).
UPDATE_NEW_CHILD_EVENT = "E1746"  # Karol Strzembosz's birth event

# --- update_event: nonexistent event id -------------------------------------
NONEXISTENT_EVENT_ID = "E9999"

# --- add_event: is_child_in_birth_event fix - additional coverage ----------
# One new parent + one already-existing parent (via existing_person_id),
# both should end up linked to the same new birth event.
MIXED_PARENT_EXISTING_FATHER = UNRELATED_MALE  # P0038, reused

# An existing person already holding 'father' role as its own top-level
# participant, alongside a *new* child whose parent_father is a different,
# new person - both end up linked as 'father' to the same event (the fix
# has no "role slot already taken by someone else" guard, unlike
# sync_parents_to_birth_events - see test docstring).
CONFLICTING_FATHER = "P0046"  # Jan Krakowiak (M), no birth event on file

# --- update_event: new child+parents combined with pre-existing unrelated
# participants in the same update call, to check EP id sequencing ----------
COMBINED_SETUP_CHILD = "P0055"  # Adam Wolski (M), no birth event - placeholder, gets replaced
COMBINED_WITNESS_1 = "P0068"    # Petronella Surdey (F), no birth event
COMBINED_WITNESS_2 = "P0043"    # Anna Morawinska (F), no birth event

# --- sync_parents_to_birth_events (the "<role>_parent_<type>" mechanism) ---
# A separate, older mechanism (used for e.g. marriage/death participants)
# for attaching a participant's own parent inline - only works with
# existing_person_id on both sides (no new-person creation path).
SYNC_GROOM = "P0073"         # Onufry Mieszala (M), no existing birth event
SYNC_GROOM_FATHER = "P0081"  # Franciszek Niewczas (M), existing person used as groom's father
SYNC_BRIDE = "P0089"         # Anna Orlowski (F)

# --- add_person / update_person: place resolution -------------------------
# Both endpoints route through find_or_create_place (name-only match, no
# house_number) rather than add_event/update_event's handle_place
# (name+house_number match) - a second, independently-duplicated "find or
# create place" implementation with different matching semantics.
# EXISTING_PLACE_NAME/EXISTING_PLACE_HOUSE_NUMBER and NEW_PLACE_NAME are
# reused from the add_event section above.

# --- update_person: sync-to-events branches ---------------------------------
# P0012 (see NO_BIRTH_EVENT_CHILD/PLAIN_DEATH_DECEASED above) has neither a
# birth nor a death event - exercises the "create event" branches for both.
UPDATE_PERSON_NO_EVENTS = "P0012"
# P0001 Jan Surdey already has both a birth event (E0539) and a death event
# (E0543) - exercises the "update existing event in place" branches.
UPDATE_PERSON_HAS_EVENTS = "P0001"
UPDATE_PERSON_BIRTH_EVENT = "E0539"
UPDATE_PERSON_DEATH_EVENT = "E0543"

NONEXISTENT_PERSON_ID = "P9999"

# --- delete_person -----------------------------------------------------------
# P0011 Krzysztof Salyk participates in 7 events across 5 event types/roles:
#   E0004 death/deceased   (sole participant - event should be deleted)
#   E0653 birth/child      (sole participant - event should be deleted)
#   E0555 death/witness    (2 other participants - event survives untouched)
#   E0651 birth/witness    (6 other participants - event survives untouched)
#   E0776 birth/father     (2 other participants - event survives untouched)
#   E1415 marriage/groom   (1 other participant - event survives, but now
#                            short its required groom - see test docstring)
#   E1416 marriage/groom   (same as E1415)
# One delete_person call exercises cascade-delete-when-empty,
# shrink-and-keep, AND a real, unhandled role_cardinality regression
# together.
DELETE_PERSON_ID = "P0011"

# --- delete_event ------------------------------------------------------------
# E0055: birth event with 3 participants (child P0170, father P0168, mother
# P0169) - a plain multi-participant event, no cascades expected.
DELETE_EVENT_ID = "E0055"
