#!/usr/bin/env python3
"""
Data schema normalization (Phase 0 of the Java migration - see
JAVA_MIGRATION.md and the approved plan).

Different code paths (the original process_genealogy.py parser,
add_person's auto-birth-event, add_event's participant-driven birth
events, and old migration scripts) each wrote slightly different key
sets - and different key *orders* - for the same entity type over time.
This script (a) makes every record of a type carry the same field set by
adding any canonical field it's missing, set to null (or [] for list
fields), and (b) reorders every record's keys to the single canonical
order in CANONICAL_FIELDS. Values are never renamed or overwritten -
purely additive plus a key-order rewrite.

The key-order pass matters for the Java migration specifically: Java
records always serialize their fields in one fixed declared order, so a
lossless load-then-save round trip (JAVA_MIGRATION.md step 1's exit
criterion) is only byte-identical if every record of a type already has
the same on-disk key order. Before this pass, real records of the same
type had multiple different orders (e.g. some persons had "gender"
before "maiden_name", some after) - a residue of Phase 0 only having
closed the field *set*, not the field *order*.

Writes to a NEW file (does not touch the source) so the result can be
reviewed and diffed before anything is promoted:

    python normalize_data_schema.py [input_path] [output_path]

Defaults: input=data/genealogy_new_model.json,
output=data/genealogy_new_model.normalized.json
"""
import json
import sys
from collections import Counter

CANONICAL_FIELDS = {
    'persons': ['id', 'first_name', 'last_name', 'gender', 'maiden_name', 'occupation', 'tags', 'notes'],
    'events': ['id', 'type', 'date', 'place_id', 'content', 'description', 'title', 'source', 'notes', 'tags', 'links'],
    'places': ['id', 'name', 'parish_name', 'house_number', 'type'],
    'event_participations': ['id', 'event_id', 'person_id', 'role'],
}

LIST_FIELDS = {'tags', 'links'}

# FlexibleDate.to_dict() (new_data_model.py) omits year/month/day/circa keys
# entirely when falsy, but some events' "date" sub-object was instead built
# via a dict literal that always includes year/month/day (circa still
# omitted when false) - a second inconsistent shape Phase 0 never touched
# since it only normalized top-level entity keys, not nested ones. This
# closes that gap the same way: year/month/day always present (null if
# unknown), circa always present (a plain bool, never omitted).
DATE_FIELDS = ['year', 'month', 'day', 'circa']


def normalize_event_dates(events):
    changed_count = 0
    samples = []
    for event_id, event in events.items():
        date = event.get('date')
        if date is None or list(date.keys()) == DATE_FIELDS:
            continue

        before = dict(date)
        event['date'] = {
            'year': date.get('year'),
            'month': date.get('month'),
            'day': date.get('day'),
            'circa': bool(date.get('circa', False)),
        }
        changed_count += 1
        if len(samples) < 3:
            samples.append((event_id, before, dict(event['date'])))
    return changed_count, samples


def normalize_entity(records, fields):
    added_counts = Counter()
    reordered_count = 0
    changed_count = 0
    samples = []
    for record_id, record in records.items():
        missing = [f for f in fields if f not in record]
        needs_reorder = list(record.keys()) != fields
        changed = bool(missing) or needs_reorder
        before = dict(record) if changed and len(samples) < 3 else None

        for field in missing:
            record[field] = [] if field in LIST_FIELDS else None
            added_counts[field] += 1
        if needs_reorder:
            reordered_count += 1
        if changed:
            changed_count += 1

        # Rebuild in canonical order. Any key not in `fields` shouldn't exist
        # post-Phase-0, but is preserved (appended) rather than dropped, just
        # in case.
        extra_keys = [k for k in record.keys() if k not in fields]
        reordered = {f: record[f] for f in fields}
        for key in extra_keys:
            reordered[key] = record[key]
        records[record_id] = reordered

        if before is not None:
            samples.append((record_id, before, dict(reordered)))
    return added_counts, reordered_count, changed_count, samples


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else 'data/genealogy_new_model.json'
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'data/genealogy_new_model.normalized.json'

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {input_path}")
    print()

    date_changed_count, date_samples = normalize_event_dates(data.get('events', {}))
    print(f"=== events[*].date shape ({DATE_FIELDS}) ===")
    if not date_changed_count:
        print("  already consistent")
    else:
        print(f"  normalized shape on {date_changed_count} record(s)")
        print()
        print(f"  sample ({len(date_samples)} of {date_changed_count} changed record(s)):")
        for event_id, before, after in date_samples:
            print(f"    {event_id}")
            print(f"      before: {before}")
            print(f"      after:  {after}")
    print()

    for entity_key, fields in CANONICAL_FIELDS.items():
        records = data.get(entity_key, {})
        added_counts, reordered_count, changed_count, samples = normalize_entity(records, fields)

        print(f"=== {entity_key} ({len(records)} records) ===")
        if not added_counts and not reordered_count:
            print("  already consistent - no fields added, no keys reordered")
        else:
            if not added_counts:
                print("  no fields added (field set was already closed)")
            for field, count in added_counts.most_common():
                print(f"  + {field}: added to {count} record(s)")
            print(f"  reordered keys on {reordered_count} record(s) to match {fields}")
            print()
            print(f"  sample ({len(samples)} of {changed_count} changed record(s)):")
            for record_id, before, after in samples:
                print(f"    {record_id}")
                print(f"      before: {before}")
                print(f"      after:  {after}")
        print()

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Wrote normalized copy to {output_path}")
    print("Source file was NOT modified. Review the output above, then diff/promote manually.")


if __name__ == '__main__':
    main()
