"""
Layer 1 golden-master helpers.

A "golden fixture" for a scenario is the JSON-serializable diff between the
sandboxed data file before and after one API call, plus the API response.
Diffing (rather than storing the whole ~1300-person file) keeps fixtures
readable: only what the call actually touched shows up.

First run for a given name: writes tests/golden/<name>.json from the actual
result and fails on purpose, so a new fixture always gets one human look
before it's trusted. Every run after: asserts an exact match.

The real data file (data/genealogy_new_model.json, copied into each test's
sandbox - see conftest.py) keeps growing as genealogy work happens, so the
id counters new records get (P####/PL####/E####/EP####) drift over time.
Fixtures must not pin that drift: any id a call *creates* (i.e. any key
under one of the diff's "added" maps) is replaced with a stable placeholder
like "E_NEW_1" everywhere it appears - in the diff and in the response -
before comparing against or writing the fixture. Pre-existing ids (the
anchors in tests/anchors.py) are untouched since they never appear in
"added". A test whose scenario needs an uncovered setup call first (see
test_update_event.py's combined test) passes that call's own diff as
assert_matches_golden's extra_new_id_diffs so its ids get normalized too,
even though only the main diff is persisted to the fixture.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from invariants import run_all_checks

GOLDEN_DIR = Path(__file__).parent / "golden"

ENTITY_KEYS = ("persons", "places", "events", "event_participations")
ID_PLACEHOLDER_PREFIXES = {
    "persons": "P",
    "places": "PL",
    "events": "E",
    "event_participations": "EP",
}


def dict_diff(before: dict, after: dict) -> dict:
    """added/removed/changed keys between two id->record dicts."""
    added = {k: v for k, v in after.items() if k not in before}
    removed = {k: v for k, v in before.items() if k not in after}
    changed = {
        k: {"before": before[k], "after": after[k]}
        for k in after
        if k in before and before[k] != after[k]
    }
    return {"added": added, "removed": removed, "changed": changed}


def state_diff(before: dict, after: dict) -> dict:
    """Per-entity-collection diff across the whole persisted data file."""
    return {key: dict_diff(before.get(key, {}), after.get(key, {})) for key in ENTITY_KEYS}


def _new_id_placeholders(*diffs: dict) -> dict[str, str]:
    """Map every id created across the given diffs (in the order passed) to
    a stable placeholder, ordered within each entity type by numeric id
    value - which matches creation order, since ids are assigned from a
    strictly-increasing counter - so the mapping, and thus the fixture,
    stays the same across runs no matter where the live dataset's counter
    currently sits.

    Accepts more than one diff for scenarios that need setup calls the
    fixture itself doesn't cover (e.g. creating an event via add-event just
    to get a real event_id to pass to update-event): pass the setup step's
    diff first so its ids are normalized too, even though only the main
    diff is what gets persisted to the fixture."""
    mapping: dict[str, str] = {}
    for entity_key, prefix in ID_PLACEHOLDER_PREFIXES.items():
        seen_ids: dict[str, None] = {}
        for diff in diffs:
            for real_id in diff.get(entity_key, {}).get("added", {}):
                seen_ids[real_id] = None
        ordered = sorted(seen_ids, key=lambda rid: int(re.sub(r"\D", "", rid) or 0))
        for i, real_id in enumerate(ordered, start=1):
            mapping[real_id] = f"{prefix}_NEW_{i}"
    return mapping


def _normalize_new_ids(actual: dict, extra_diffs: list[dict] | None = None) -> dict:
    """Replace every created-id occurrence (in the diff and in the response
    - e.g. response['message'] embeds ids as plain text) with its
    placeholder from _new_id_placeholders."""
    mapping = _new_id_placeholders(*(extra_diffs or []), actual.get("diff", {}))
    if not mapping:
        return actual
    text = json.dumps(actual, ensure_ascii=False)
    for real_id, placeholder in mapping.items():
        text = re.sub(rf"\b{re.escape(real_id)}\b", placeholder, text)
    return json.loads(text)


def assert_matches_golden(name: str, actual: dict, extra_new_id_diffs: list[dict] | None = None) -> None:
    GOLDEN_DIR.mkdir(exist_ok=True)
    path = GOLDEN_DIR / f"{name}.json"
    actual = _normalize_new_ids(actual, extra_new_id_diffs)
    serialized = json.dumps(actual, indent=2, ensure_ascii=False, sort_keys=True)

    if not path.exists():
        path.write_text(serialized, encoding="utf-8")
        raise AssertionError(
            f"No golden fixture yet - wrote a new one from this run's output: {path}\n"
            f"Review it, then re-run the test so it's checked against a fixture "
            f"instead of writing one."
        )

    expected = path.read_text(encoding="utf-8")
    assert serialized == expected, (
        f"Result diverged from golden fixture {path}.\n"
        f"If this divergence is an intended behavior change, delete the fixture "
        f"and re-run to regenerate it."
    )


def assert_no_new_invariant_issues(before_state: dict, after_state: dict) -> None:
    """Layer 2 regression guard: a single API call must not introduce a new
    invariant-check issue code, or increase the count of an existing one,
    relative to the pre-call baseline (real data already has pre-existing
    issues, so "zero issues" isn't a usable bar)."""
    before_counts = Counter(issue.code for issue in run_all_checks(before_state))
    after_counts = Counter(issue.code for issue in run_all_checks(after_state))

    new_codes = set(after_counts) - set(before_counts)
    assert not new_codes, f"Call introduced new invariant issue code(s): {sorted(new_codes)}"

    increased = {
        code: (before_counts[code], after_counts[code])
        for code in after_counts
        if after_counts[code] > before_counts.get(code, 0)
    }
    assert not increased, f"Call increased existing invariant issue count(s): {increased}"
