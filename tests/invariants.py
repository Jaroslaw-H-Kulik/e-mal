"""
Layer 2: structural/consistency checks over a genealogy_new_model.json snapshot.

Deliberately independent of the HTTP API and of pytest - these are plain
functions over the same dict shape GET /data/genealogy_new_model.json
returns, so they can run standalone against a file on disk:

    uv run python tests/invariants.py [path/to/genealogy_new_model.json]

...or be reused inside pytest tests (Layer 1) to check that a live sandboxed
server didn't introduce new inconsistencies after a POST.

Age-based checks (person too young/old for a role, per improvements.txt
step 23) are intentionally NOT included yet - they require inferring each
person's birth year from their birth events, which is involved enough to
deserve its own pass once Layer 1 has pinned down how birth events actually
behave.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Issue:
    severity: str  # "error" or "warning"
    code: str
    message: str


def check_dangling_participation_refs(data: dict) -> list[Issue]:
    persons = data.get("persons", {})
    events = data.get("events", {})
    issues = []
    for ep_id, ep in data.get("event_participations", {}).items():
        if ep.get("event_id") not in events:
            issues.append(Issue(
                "error", "dangling_event_ref",
                f"event_participation {ep_id} references missing event {ep.get('event_id')}",
            ))
        if ep.get("person_id") not in persons:
            issues.append(Issue(
                "error", "dangling_person_ref",
                f"event_participation {ep_id} references missing person {ep.get('person_id')}",
            ))
    return issues


def check_dangling_place_refs(data: dict) -> list[Issue]:
    places = data.get("places", {})
    issues = []
    for event_id, event in data.get("events", {}).items():
        place_id = event.get("place_id")
        if place_id and place_id not in places:
            issues.append(Issue(
                "error", "dangling_place_ref",
                f"event {event_id} references missing place {place_id}",
            ))
    return issues


def check_duplicate_participations(data: dict) -> list[Issue]:
    """Same person holding the same role in the same event more than once."""
    seen = Counter()
    for ep in data.get("event_participations", {}).values():
        seen[(ep.get("event_id"), ep.get("person_id"), ep.get("role"))] += 1
    return [
        Issue(
            "error", "duplicate_participation",
            f"person {person_id} holds role '{role}' in event {event_id} {count} times",
        )
        for (event_id, person_id, role), count in seen.items()
        if count > 1
    ]


def check_person_multiple_roles_same_event(data: dict) -> list[Issue]:
    """improvements.txt step 23: a person cannot hold two roles in one event."""
    roles_by_event_person = defaultdict(set)
    for ep in data.get("event_participations", {}).values():
        roles_by_event_person[(ep.get("event_id"), ep.get("person_id"))].add(ep.get("role"))
    return [
        Issue(
            "error", "multiple_roles_same_event",
            f"person {person_id} holds multiple roles {sorted(roles)} in event {event_id}",
        )
        for (event_id, person_id), roles in roles_by_event_person.items()
        if len(roles) > 1
    ]


def check_role_cardinality(data: dict) -> list[Issue]:
    """birth needs exactly one child, marriage exactly one bride + one groom,
    death exactly one deceased."""
    role_counts_by_event = defaultdict(Counter)
    for ep in data.get("event_participations", {}).values():
        role_counts_by_event[ep.get("event_id")][ep.get("role")] += 1

    expectations = {
        "birth": {"child": 1},
        "marriage": {"bride": 1, "groom": 1},
        "death": {"deceased": 1},
    }
    issues = []
    for event_id, event in data.get("events", {}).items():
        expected = expectations.get(event.get("type"))
        if not expected:
            continue
        actual = role_counts_by_event.get(event_id, Counter())
        for role, expected_count in expected.items():
            actual_count = actual.get(role, 0)
            if actual_count != expected_count:
                issues.append(Issue(
                    "error", "role_cardinality",
                    f"{event.get('type')} event {event_id} has {actual_count} '{role}' "
                    f"participant(s), expected {expected_count}",
                ))
    return issues


def check_orphan_events(data: dict) -> list[Issue]:
    """Events with zero participants. 'global' events legitimately have none."""
    participated = {ep.get("event_id") for ep in data.get("event_participations", {}).values()}
    return [
        Issue("warning", "orphan_event", f"{event.get('type')} event {event_id} has no participants")
        for event_id, event in data.get("events", {}).items()
        if event.get("type") != "global" and event_id not in participated
    ]


def check_duplicate_birth_death_events(data: dict) -> list[Issue]:
    """Step 23: a person CAN have more than one birth/death event - flagged as
    a warning to review, not asserted as always wrong."""
    events = data.get("events", {})
    child_events = defaultdict(list)
    deceased_events = defaultdict(list)
    for ep in data.get("event_participations", {}).values():
        event = events.get(ep.get("event_id"))
        if not event:
            continue
        if ep.get("role") == "child" and event.get("type") == "birth":
            child_events[ep.get("person_id")].append(ep.get("event_id"))
        if ep.get("role") == "deceased" and event.get("type") == "death":
            deceased_events[ep.get("person_id")].append(ep.get("event_id"))

    issues = [
        Issue(
            "warning", "multiple_birth_events",
            f"person {person_id} is child in {len(event_ids)} birth events: {sorted(event_ids)}",
        )
        for person_id, event_ids in child_events.items() if len(event_ids) > 1
    ]
    issues += [
        Issue(
            "warning", "multiple_death_events",
            f"person {person_id} is deceased in {len(event_ids)} death events: {sorted(event_ids)}",
        )
        for person_id, event_ids in deceased_events.items() if len(event_ids) > 1
    ]
    return issues


def check_metadata_counts(data: dict) -> list[Issue]:
    """metadata.total_* is a cached summary that can drift from reality."""
    metadata = data.get("metadata", {})
    actual = {"total_persons": len(data.get("persons", {})), "total_events": len(data.get("events", {}))}
    return [
        Issue(
            "warning", "stale_metadata",
            f"metadata.{key}={metadata[key]} but actual {key.replace('total_', '')}={actual[key]}",
        )
        for key in actual
        if key in metadata and metadata[key] != actual[key]
    ]


ALL_CHECKS = [
    check_dangling_participation_refs,
    check_dangling_place_refs,
    check_duplicate_participations,
    check_person_multiple_roles_same_event,
    check_role_cardinality,
    check_orphan_events,
    check_duplicate_birth_death_events,
    check_metadata_counts,
]


def run_all_checks(data: dict) -> list[Issue]:
    issues = []
    for check in ALL_CHECKS:
        issues.extend(check(data))
    return issues


def format_report(issues: Iterable[Issue], sample_per_code: int = 10) -> str:
    issues = list(issues)
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    by_code = Counter(i.code for i in issues)
    grouped = defaultdict(list)
    for issue in issues:
        grouped[issue.code].append(issue)

    lines = [f"Errors: {len(errors)}  Warnings: {len(warnings)}", ""]
    for code, count in by_code.most_common():
        lines.append(f"  {code}: {count}")
    lines.append("")
    for code, code_issues in grouped.items():
        lines.append(f"--- {code} ({len(code_issues)}) ---")
        for issue in code_issues[:sample_per_code]:
            lines.append(f"  [{issue.severity.upper()}] {issue.message}")
        if len(code_issues) > sample_per_code:
            lines.append(f"  ... and {len(code_issues) - sample_per_code} more")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/genealogy_new_model.json"
    with open(path, encoding="utf-8") as f:
        loaded = json.load(f)
    print(format_report(run_all_checks(loaded)))
