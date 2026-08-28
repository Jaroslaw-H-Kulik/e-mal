"""
Layer 1 golden-master helpers.

A "golden fixture" for a scenario is the JSON-serializable diff between the
sandboxed data file before and after one API call, plus the API response.
Diffing (rather than storing the whole ~1300-person file) keeps fixtures
readable: only what the call actually touched shows up.

First run for a given name: writes tests/golden/<name>.json from the actual
result and fails on purpose, so a new fixture always gets one human look
before it's trusted. Every run after: asserts an exact match.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from invariants import run_all_checks

GOLDEN_DIR = Path(__file__).parent / "golden"

ENTITY_KEYS = ("persons", "places", "events", "event_participations")


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


def assert_matches_golden(name: str, actual: dict) -> None:
    GOLDEN_DIR.mkdir(exist_ok=True)
    path = GOLDEN_DIR / f"{name}.json"
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
