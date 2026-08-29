#!/usr/bin/env python3
"""
Data schema normalization (Phase 0 of the Java migration - see
JAVA_MIGRATION.md and the approved plan).

Different code paths (the original process_genealogy.py parser,
add_person's auto-birth-event, add_event's participant-driven birth
events, and old migration scripts) each wrote slightly different key
sets for the same entity type over time, so real records of the same
type carry different fields today. This script makes every record of a
type carry the same field set by adding any canonical field it's
missing, set to null (or [] for list fields). It never removes, renames,
or overwrites an existing key/value - purely additive.

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


def normalize_entity(records, fields):
    added_counts = Counter()
    samples = []
    for record_id, record in records.items():
        before = None
        missing = [f for f in fields if f not in record]
        if missing and len(samples) < 3:
            before = dict(record)
        for field in missing:
            record[field] = [] if field in LIST_FIELDS else None
            added_counts[field] += 1
        if missing and before is not None:
            samples.append((record_id, before, dict(record)))
    return added_counts, samples


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else 'data/genealogy_new_model.json'
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'data/genealogy_new_model.normalized.json'

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {input_path}")
    print()

    for entity_key, fields in CANONICAL_FIELDS.items():
        records = data.get(entity_key, {})
        added_counts, samples = normalize_entity(records, fields)

        print(f"=== {entity_key} ({len(records)} records) ===")
        if not added_counts:
            print("  already consistent - no fields added")
        else:
            for field, count in added_counts.most_common():
                print(f"  + {field}: added to {count} record(s)")
            print()
            print(f"  sample ({min(len(samples), 3)} of {sum(added_counts.values())} changed record(s)):")
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
