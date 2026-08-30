# Testing Strategy — Summary (2026-08-27)

## Why

`server.py` is a 2800-line monolith (`GenealogyServerHandler`) that mixes HTTP
routing, business logic, persistence, HTML scraping, and GEDCOM matching in
one class. Goal is to eventually rewrite/restructure it, but there is **zero
test coverage** today, so refactoring blind is too risky. Decision: build a
safety net of tests first, do the rewrite manually/incrementally afterward.

## Key findings about the current backend

- `new_data_model.py` (clean dataclasses: `Person`, `Event`,
  `GenealogyDatabase`, ...) is **not used at runtime**. `server.py` never
  imports it — every endpoint hand-rolls raw dict read/modify/write against
  `data/genealogy_new_model.json`. Only migration scripts use the model.
- **No data-access layer.** All 17+ POST/GET handlers each do their own
  `json.load(f)` → mutate → `json.dump(f)`. No locking, no transactions, no
  shared code path.
- The data file path `'data/genealogy_new_model.json'` is a literal string
  copy-pasted in **12 places** in `server.py` — not even a constant. (This
  turned out useful: paths resolve relative to process `cwd`, which is what
  makes the test sandbox trick in `tests/conftest.py` work with zero source
  changes.)
- `_documents_dir()`/`_documents_path()` resolve relative to `__file__`
  instead of `cwd` — inconsistent with the rest of the file, but harmless as
  long as the sandbox copies `server.py` itself (which it does).
- Business logic methods are huge and full of cascading side effects accreted
  from the 68 steps in `improvements.txt`: `add_event` (~317 lines),
  `update_event` (~295 lines), `add_relationship` (~243 lines). E.g. adding a
  birth event can auto-create a marriage event, sync ages to birth years,
  dedupe witnesses/godparents, etc., all inline.
- Duplicated ID-generator helpers (`get_next_person_id`, `get_next_event_id`,
  `get_next_relationship_id`, `get_next_document_id`, ...) instead of reusing
  `new_data_model.get_next_id`.
- `run_server(port=...)` already accepts a port argument, but
  `if __name__ == '__main__': run_server(8001)` hardcodes 8001 — no CLI/env
  override. Test harness works around this by importing `server` and calling
  `run_server(<port>)` directly instead of running the file as `__main__`.
- `validate_data.py` is **dead/legacy** — targets the old flat model
  (`persons.json`/`events.json`/`relationships.json`, fields like
  `given_name`, `birth_year_estimate`) and has a hardcoded macOS path from a
  different machine. Not usable, not extended — a fresh invariant checker was
  written instead (`tests/invariants.py`).
- **Documented model vs. actual data has drifted**: `CLAUDE.md` and
  `new_data_model.py` describe `FamilyRelationship` (`R####`) as a stored
  entity. The live `data/genealogy_new_model.json` has **no
  `family_relationships` key at all** — only `persons`, `places`, `events`,
  `event_participations`, `metadata`. Relationships are apparently derived
  from `event_participations` on the fly.
- `metadata.total_persons`/`total_events` in the data file are stale (601 vs
  actual 1299 persons; 501 vs actual 1968 events) — this cached summary is
  never kept in sync and shouldn't be trusted.

## Decisions made

1. **Test-first, not rewrite-first.** Build characterization/black-box tests
   against the current behavior before touching production code.
2. **No mocking, no unit tests with mocks.** High-level tests only: call the
   real HTTP API (`POST /api/...`), then verify persisted state via
   `GET /data/genealogy_new_model.json` — the same endpoint the frontend
   itself uses to load data. This is also more rigorous than trusting POST
   response bodies, since some handlers (e.g. `add_event`) only return the
   new event/persons, not full state.
3. **Dependency management: `uv`.** Repo had zero dependency management
   before. Chose `uv` over `poetry`/plain `venv` — modern, single tool,
   lockfile (`uv.lock`), minimal ceremony, nothing else installed previously
   so no migration cost.
4. **`pytest` + `requests`** as dev dependencies (industry standard for this
   kind of integration/E2E testing).
5. **Constraint: no production code changes** without asking first. Test
   setup only adds new files (`tests/`, `pyproject.toml`, `uv.lock`,
   `.gitignore`). Confirmed via `git status` after each step that nothing
   under `server.py`, `web/`, or `data/` changed.
6. **geneteka-import endpoint is explicitly out of scope for now** — it
   doesn't fit the "POST then GET to verify" pattern (hits a live external
   site, doesn't mutate `genealogy_new_model.json`). `gedcom-lookup` was in
   the same boat but has since been removed entirely — see "Feature
   removed: GEDCOM lookup/import" below.

## Priority order (agreed)

1. **Layer 0** — sandbox test harness (done)
2. **Layer 2** — standalone data-invariant checks (done, baseline captured)
3. **Layer 1** — golden-master/characterization tests for the highest-risk
   endpoints first: `add_event`, `update_event`, `add_relationship` (done —
   `tests/test_add_event.py`, `tests/test_update_event.py`,
   `tests/test_add_relationship.py`)
4. **Layer 1** — golden-master tests for remaining endpoints (done —
   `tests/test_add_person.py`, `tests/test_update_person.py`,
   `tests/test_delete_person.py`, `tests/test_delete_event.py`; document
   CRUD and the geneteka-import endpoint remain uncovered, see
   below). 35 tests pass total (`uv run pytest tests/`).
5. **Layer 3** — unit tests for near-pure helper methods, as prep for
   extracting them into a service layer (not started)

## Feature removed: GEDCOM Enrichment Review (2026-08-28)

`apply_enrichment`/`/api/apply-enrichment` was found to be completely
broken against the current data model (see below) - it was removed
entirely rather than fixed, along with its UI (`web/enrichment.js`, the
enrichment modal + toolbar button in `index.html`, the two wrapper methods
in `app.js`, and the CSS block in `style.css`) and its test file
(`test_apply_enrichment.py`). `generate_enrichment_queue.py` (which
populated the queue this UI read from) is now orphaned but was left in
place - out of scope for this pass. `add_relationship`/`/api/add-relationship`
(a different, working, still-tested feature) was NOT touched.

## Feature removed: GEDCOM lookup/import (2026-08-30)

GEDCOM cross-referencing (`/api/gedcom-lookup`, `/api/gedcom-person/<id>`,
and all of their UI - the Data Source model-switcher tabs, both "Search in
GEDCOM" sections on the Add/Edit Person modals, and the GEDCOM
relationship add/merge modal in `editor.js`) was removed wholesale, along
with `data/gedcom_model.json`, `convert_gedcom_to_model.py`, and
`enrich_from_gedcom.py`. `base.ged` (the raw export) was left in place as
source data. The already-orphaned `generate_enrichment_queue.py` and
`data/enrichment_queue.json` (dead since the GEDCOM Enrichment Review
removal above) were deleted in the same pass.

`add_person`'s dual-key-shape fallback (`given_name`/`first_name`,
`birth_year_estimate`/`birth_date`) was simplified to just
`given_name`/`birth_year_estimate` — the only caller that ever sent the
other shape was `editor.js`'s GEDCOM "add relationship as new person"
flow (confirmed via `tests/test_add_person.py`'s docstring); the real Add
Person form only ever sent the first shape. `tests/golden/add_person_first_last_name_shape.json`
and its test were removed along with it. The Java port
(`service/PersonService.java`) was updated to match, and `JAVA_MIGRATION.md`'s
migration order no longer lists GEDCOM endpoints/parser steps as a
consequence.

Also removed as part of the same cleanup pass (not GEDCOM-related, but
found while auditing the toolbar): the "View Changes"/"Export Data"
buttons and the `this.changes` in-memory edit/merge log backing them, and
the "Reset" view button. `saveMergeLogToServer()`/`/api/save-merge-log`/
`GenealogyRepository.save_merge_log` (an auto-save side-channel writing
`data/merge_log.json` for `process_genealogy_v2.py` to consume on
reparse) went with it, since it read from the same `this.changes` array
and had no other caller. Person merging itself (`openMergeModal`/
`executeMerge`) is untouched.

## Bugs/gaps found by the Layer 1 tests

- **`delete_person` can silently break required-role cardinality** (open,
  left as-is for now): it removes a person's participations and only
  deletes an event if it becomes fully empty. If a person held a
  cardinality-required role (`groom`/`bride` on a marriage, `deceased` on
  a death, `child` on a birth) and other participants remain, the event
  survives short that role with no warning. Pinned in
  `test_delete_person.py` by asserting the `role_cardinality` invariant
  count increases by exactly 2 for the tested scenario (two marriages
  losing their groom).
- **Fixed (2026-08-28): `delete_person`'s `deleted_events` response field
  had non-deterministic order** — built from a `set()`, so iteration order
  depended on Python's per-process string hash randomization. Fixed by
  sorting `events_to_check` before iterating it in `delete_person`.
- **Fixed (2026-08-28): `add_person`/`update_person` duplicated the "find
  or create place" logic** as a separate implementation
  (`find_or_create_place`, name-only match) from the one
  `add_event`/`update_event` used (`handle_place`, name+house_number
  match) — same duplication problem already flagged for ID generation,
  just for places. Unified into one `resolve_place(places, name,
  house_number=None)`: `house_number=None` preserves the name-only match
  (add_person/update_person callers); a real value preserves the
  name+house_number match (`handle_place` is now a thin wrapper around
  it). Both call sites' matching behavior is unchanged — verified by the
  full test suite passing unmodified except for the ordering fix above.
- **`update_person` branches on key presence, not truthiness**: the real
  UI (`savePersonEdit` in `editor.js`) always sends `place_of_birth`/
  `place_of_death` (null when blank). For a person who already has birth/
  death events, this means `updated_events` in the response always lists
  those event ids, even when the null values mean nothing inside them
  actually changed.

## What's built so far

- `pyproject.toml` / `uv.lock` — `uv`-managed project, dev deps `pytest`,
  `requests`. `testpaths = ["tests"]` configured so pytest doesn't also try
  to collect the unrelated `test_pretrained.py` at repo root.
- `.gitignore` — `.venv/`, `__pycache__/`, `*.pyc`.
- `tests/conftest.py` — `live_server` pytest fixture. Per test: copies
  `server.py` + `web/` + `data/genealogy_new_model.json` +
  `data/documents.json` into a fresh temp dir, launches `server.py` as a
  subprocess (`import server; server.run_server(<free_port>)`) with that temp
  dir as `cwd`, waits for it to come up, yields a `LiveServer` handle
  (`.get_state()` = GET the full data file, `.post(endpoint, payload)`),
  tears down after. Fully isolated from real data — nothing a test does can
  touch `data/genealogy_new_model.json` on disk.
- `tests/test_smoke.py` — proves the harness itself works (server starts,
  serves sandboxed state, isolation confirmed).
- `tests/invariants.py` — Layer 2 structural/consistency checks, importable
  functions + CLI entry point (`python tests/invariants.py [path]`).
  Deliberately does **not** yet include age-based checks (person too
  young/old for a role) — needs per-person birth-year inference from birth
  events, planned as a follow-up pass.

## Layer 2 baseline (real data, captured 2026-08-27)

Read-only diagnostic run against `data/genealogy_new_model.json` — no data
was changed.

| Check | Count | Meaning |
|---|---|---|
| `multiple_roles_same_event` | 81 errors | Same person, 2 roles in 1 event. Mostly plausible `godparent`+`witness` overlaps, but some are real bugs (e.g. P0350 is both `child` and `father` in E0183). |
| `role_cardinality` | 53 errors | Birth/marriage/death event missing its required role (e.g. death event with no `deceased`). |
| `orphan_event` | 41 warnings | Birth/death events with zero participants at all. |
| `multiple_birth_events` | 27 warnings | Person is `child` in 2+ birth events. |
| `multiple_death_events` | 13 warnings | Person is `deceased` in 2+ death events (one person, P0237, has 3). |
| `stale_metadata` | 2 warnings | `metadata.total_persons`/`total_events` don't match actual counts. |

These line up with bugs the user had already suspected (`improvements.txt`
steps 23 and 28), confirming the invariant checks are catching real things.
**Not yet fixed** — this is a baseline, not a cleanup pass.

## Open / unresolved decisions

- How to wire the Layer 2 baseline into pytest as a regression guard: since
  real data already has 134 pre-existing errors, a test can't assert "zero
  issues". Proposed but not yet agreed: snapshot the current baseline and
  fail only if a change *increases* the count or introduces a *new issue
  code* — not yet implemented.
- Whether/when to actually fix the real data issues found by Layer 2 —
  deferred, not decided.
- Framework question (keep stdlib `http.server` vs. move to
  Flask/FastAPI) and big-bang-vs-incremental rewrite question were raised
  early on but never answered — testing work took priority. Still open.

## CLI cheat sheet

See `COMMANDS.m` in repo root for the full list of commands (run via
`python -m uv run ...` since `uv` is not on this shell's PATH — installed
with `pip install --user uv`).

## Next step

Layer 1: golden-master tests for `add_event`, `update_event`,
`add_relationship` — build representative request payloads using real IDs
from the dataset, capture response + resulting `GET /data/...` state as
committed fixtures, assert future runs match exactly.
