#!/usr/bin/env python3
"""
Data Validation and Quality Report
Validates the structured genealogical data and generates quality reports
"""

import json
from collections import defaultdict
from typing import Dict, List, Set


class DataValidator:
    """Validates genealogical data quality"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.persons = {}
        self.events = {}
        self.relationships = {}
        self.errors = []
        self.warnings = []
        self.load_data()

    def load_data(self):
        """Load all JSON data"""
        with open(f"{self.data_dir}/persons.json", 'r', encoding='utf-8') as f:
            self.persons = json.load(f)

        with open(f"{self.data_dir}/events.json", 'r', encoding='utf-8') as f:
            self.events = json.load(f)

        with open(f"{self.data_dir}/relationships.json", 'r', encoding='utf-8') as f:
            self.relationships = json.load(f)

    def validate_person_references(self):
        """Check that all person IDs referenced in events exist"""
        print("Validating person references...")

        missing_persons = set()

        for event_id, event in self.events.items():
            # Check all person references
            person_fields = ['child', 'father', 'mother', 'deceased', 'groom', 'bride']
            for field in person_fields:
                if field in event and event[field]:
                    if event[field] not in self.persons:
                        missing_persons.add(event[field])
                        self.errors.append(f"Event {event_id}: references non-existent person {event[field]}")

            # Check witness lists
            for witness_id in event.get('witnesses', []):
                if witness_id not in self.persons:
                    missing_persons.add(witness_id)
                    self.errors.append(f"Event {event_id}: references non-existent witness {witness_id}")

            # Check godparent lists
            for gp_id in event.get('godparents', []):
                if gp_id not in self.persons:
                    missing_persons.add(gp_id)
                    self.errors.append(f"Event {event_id}: references non-existent godparent {gp_id}")

        if not missing_persons:
            print("  ✓ All person references are valid")
        else:
            print(f"  ✗ Found {len(missing_persons)} missing person references")

    def validate_temporal_consistency(self):
        """Check for temporal impossibilities"""
        print("Validating temporal consistency...")

        issues = 0

        for rel_id, rel in self.relationships.items():
            if rel['type'] == 'biological_parent':
                parent_id = rel['from_person']
                child_id = rel['to_person']

                parent = self.persons.get(parent_id)
                child = self.persons.get(child_id)

                if not parent or not child:
                    continue

                # Check if parent birth year < child birth year
                if parent.get('birth_year_estimate') and child.get('birth_year_estimate'):
                    parent_birth = parent['birth_year_estimate']
                    child_birth = child['birth_year_estimate']

                    if parent_birth >= child_birth:
                        issues += 1
                        self.errors.append(
                            f"Temporal impossibility: {parent['given_name']} {parent['surname']} "
                            f"(b.{parent_birth}) cannot be parent of "
                            f"{child['given_name']} {child['surname']} (b.{child_birth})"
                        )
                    elif child_birth - parent_birth < 15:
                        issues += 1
                        self.warnings.append(
                            f"Unlikely: {parent['given_name']} {parent['surname']} "
                            f"(b.{parent_birth}) was only {child_birth - parent_birth} when "
                            f"{child['given_name']} {child['surname']} was born"
                        )

        if issues == 0:
            print("  ✓ No temporal inconsistencies found")
        else:
            print(f"  ⚠ Found {issues} temporal issues")

    def check_orphans(self):
        """Find persons with no relationships"""
        print("Checking for orphaned persons...")

        # Get all persons mentioned in relationships
        connected_persons = set()
        for rel in self.relationships.values():
            connected_persons.add(rel['from_person'])
            connected_persons.add(rel['to_person'])

        # Find persons not in any relationship
        orphans = []
        for pid in self.persons.keys():
            if pid not in connected_persons:
                orphans.append(pid)

        print(f"  Found {len(orphans)} persons with no relationships ({len(orphans)/len(self.persons)*100:.1f}%)")

        if orphans:
            print(f"  Sample orphans:")
            for pid in orphans[:5]:
                person = self.persons[pid]
                print(f"    {pid}: {person['given_name']} {person['surname']}")

    def check_data_completeness(self):
        """Check completeness of person data"""
        print("Checking data completeness...")

        stats = {
            'with_birth_year': 0,
            'with_death_year': 0,
            'with_gender': 0,
            'with_occupation': 0,
            'with_maiden_name': 0,
        }

        for person in self.persons.values():
            if person.get('birth_year_estimate'):
                stats['with_birth_year'] += 1
            if person.get('death_year_estimate'):
                stats['with_death_year'] += 1
            if person.get('gender') and person['gender'] != 'U':
                stats['with_gender'] += 1
            if person.get('occupations'):
                stats['with_occupation'] += 1
            if person.get('maiden_name'):
                stats['with_maiden_name'] += 1

        total = len(self.persons)
        print(f"  Birth year: {stats['with_birth_year']}/{total} ({stats['with_birth_year']/total*100:.1f}%)")
        print(f"  Death year: {stats['with_death_year']}/{total} ({stats['with_death_year']/total*100:.1f}%)")
        print(f"  Gender: {stats['with_gender']}/{total} ({stats['with_gender']/total*100:.1f}%)")
        print(f"  Occupation: {stats['with_occupation']}/{total} ({stats['with_occupation']/total*100:.1f}%)")
        print(f"  Maiden name: {stats['with_maiden_name']}/{total} ({stats['with_maiden_name']/total*100:.1f}%)")

    def check_family_completeness(self):
        """Check family structure completeness"""
        print("Checking family structure completeness...")

        # For each birth event, check if both parents are recorded
        incomplete_families = []

        for event_id, event in self.events.items():
            if event['type'] == 'birth':
                has_father = event.get('father') is not None
                has_mother = event.get('mother') is not None

                if not has_father or not has_mother:
                    incomplete_families.append({
                        'event_id': event_id,
                        'child': event.get('child'),
                        'father': has_father,
                        'mother': has_mother,
                        'year': event['date'].get('year')
                    })

        print(f"  Birth events with missing parents: {len(incomplete_families)}/{len([e for e in self.events.values() if e['type'] == 'birth'])}")

        if incomplete_families:
            print(f"  Sample incomplete families:")
            for family in incomplete_families[:3]:
                child_id = family['child']
                if child_id:
                    child = self.persons.get(child_id, {})
                    print(f"    {family['year']}: {child.get('given_name', '?')} - Father: {family['father']}, Mother: {family['mother']}")

    def find_interesting_patterns(self):
        """Find interesting patterns in the data"""
        print("\nInteresting patterns:")

        # Godparents who appear multiple times
        godparent_counts = defaultdict(int)
        for rel in self.relationships.values():
            if rel['type'] == 'godparent':
                godparent_counts[rel['from_person']] += 1

        top_godparents = sorted(godparent_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\nTop 5 most frequent godparents:")
        for pid, count in top_godparents:
            person = self.persons[pid]
            print(f"  {person['given_name']} {person['surname']} ({pid}): {count} times")

        # People with most children
        parent_counts = defaultdict(int)
        for rel in self.relationships.values():
            if rel['type'] == 'biological_parent':
                parent_counts[rel['from_person']] += 1

        top_parents = sorted(parent_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\nTop 5 parents with most recorded children:")
        for pid, count in top_parents:
            person = self.persons[pid]
            print(f"  {person['given_name']} {person['surname']} ({pid}): {count} children")

        # Longest lifespan
        lifespans = []
        for pid, person in self.persons.items():
            if person.get('birth_year_estimate') and person.get('death_year_estimate'):
                lifespan = person['death_year_estimate'] - person['birth_year_estimate']
                lifespans.append((pid, person, lifespan))

        lifespans.sort(key=lambda x: x[2], reverse=True)
        print(f"\nTop 5 longest recorded lifespans:")
        for pid, person, lifespan in lifespans[:5]:
            print(f"  {person['given_name']} {person['surname']} ({pid}): {lifespan} years ({person['birth_year_estimate']}-{person['death_year_estimate']})")

    def generate_report(self):
        """Generate complete validation report"""
        print("=" * 70)
        print("DATA VALIDATION REPORT")
        print("=" * 70)
        print()

        # Basic stats
        print("Dataset Overview:")
        print(f"  Persons: {len(self.persons)}")
        print(f"  Events: {len(self.events)}")
        print(f"  Relationships: {len(self.relationships)}")
        print()

        # Run all validation checks
        self.validate_person_references()
        print()

        self.validate_temporal_consistency()
        print()

        self.check_orphans()
        print()

        self.check_data_completeness()
        print()

        self.check_family_completeness()
        print()

        self.find_interesting_patterns()
        print()

        # Summary
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Errors: {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")

        if self.errors:
            print("\nErrors found:")
            for error in self.errors[:10]:
                print(f"  - {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more")

        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings[:10]:
                print(f"  - {warning}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more")

        if not self.errors:
            print("\n✓ Data validation passed with no errors!")

        print()


def main():
    data_dir = "/Users/kulikj01/Desktop/git/mein/mal/data"

    validator = DataValidator(data_dir)
    validator.generate_report()


if __name__ == "__main__":
    main()
