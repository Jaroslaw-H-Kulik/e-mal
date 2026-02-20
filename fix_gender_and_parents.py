#!/usr/bin/env python3
"""
Gender and Parent Relationship Validator/Fixer

Fixes:
1. Gender classification using Polish naming rules (names ending in 'a' = female)
2. Parent relationships (must be male + female, never same gender)
3. Biological impossibilities
"""

import json
from collections import defaultdict


class GenderFixer:
    """Fix gender classifications and validate parent relationships"""

    def __init__(self):
        self.persons = {}
        self.events = {}
        self.relationships = {}
        self.stats = {
            'gender_fixed': 0,
            'parent_relationships_checked': 0,
            'impossible_relationships': 0,
            'relationships_fixed': 0
        }

    def load_data(self, filepath: str):
        """Load current data"""
        print(f"Loading data from: {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.persons = data.get('persons', {})
        self.events = data.get('events', {})
        self.relationships = data.get('relationships', {})

        print(f"✓ Loaded {len(self.persons)} persons")
        print(f"✓ Loaded {len(self.events)} events")
        print(f"✓ Loaded {len(self.relationships)} relationships")

    def infer_gender_from_name(self, given_name: str) -> str:
        """
        Infer gender from Polish first name.
        Rule: Names ending in 'a', 'ia', 'ja' are FEMALE
              Other endings are MALE
        """
        if not given_name:
            return 'U'

        # Handle compound names (e.g., "Jan Kapistran")
        name_parts = given_name.split()
        primary_name = name_parts[0]

        # Known male exceptions that end in 'a'
        male_exceptions = {
            'Kuba', 'Kosma', 'Barnaba', 'Bonawentura',
            'Kapistran', 'Juda', 'Elia'
        }

        if primary_name in male_exceptions:
            return 'M'

        # Known female exceptions that don't end in 'a'
        # (usually transcription errors or unusual variants)
        female_exceptions = {
            'Jadwigaz',  # Variant/error of Jadwiga
        }

        if primary_name in female_exceptions:
            return 'F'

        # Female names end in 'a', 'ia', 'ja'
        if primary_name.endswith(('a', 'ia', 'ja')):
            return 'F'

        # Everything else is male
        return 'M'

    def fix_all_genders(self):
        """Fix gender for all persons based on their names"""
        print("\nFixing gender classifications...")

        for person_id, person in self.persons.items():
            given_name = person.get('given_name', '')
            current_gender = person.get('gender', 'U')
            correct_gender = self.infer_gender_from_name(given_name)

            if current_gender != correct_gender:
                person['gender'] = correct_gender
                self.stats['gender_fixed'] += 1
                print(f"  Fixed: {given_name} ({person.get('surname', '')}) "
                      f"{current_gender} → {correct_gender}")

        print(f"✓ Fixed {self.stats['gender_fixed']} gender classifications")

    def validate_parent_relationships(self):
        """Validate all parent-child relationships"""
        print("\nValidating parent relationships...")

        # Group relationships by child
        children_parents = defaultdict(list)
        for rel_id, rel in list(self.relationships.items()):
            if rel['type'] == 'biological_parent':
                child_id = rel['to_person']
                parent_id = rel['from_person']
                children_parents[child_id].append({
                    'rel_id': rel_id,
                    'parent_id': parent_id,
                    'role': rel.get('role')
                })

        # Check each child's parents
        for child_id, parents in children_parents.items():
            self.stats['parent_relationships_checked'] += 1

            if len(parents) < 2:
                continue  # Only one parent, can't validate

            # Check if both parents are same gender (impossible!)
            parent_genders = []
            for p in parents:
                parent = self.persons.get(p['parent_id'])
                if parent:
                    parent_genders.append({
                        'id': p['parent_id'],
                        'gender': parent.get('gender', 'U'),
                        'name': f"{parent.get('given_name', '')} {parent.get('surname', '')}",
                        'rel_id': p['rel_id'],
                        'role': p['role']
                    })

            # Check for biological impossibilities
            if len(parent_genders) >= 2:
                gender1 = parent_genders[0]['gender']
                gender2 = parent_genders[1]['gender']

                # Both male or both female = impossible!
                if gender1 == gender2 and gender1 != 'U':
                    self.stats['impossible_relationships'] += 1
                    child = self.persons.get(child_id, {})
                    child_name = f"{child.get('given_name', '')} {child.get('surname', '')}"

                    print(f"\n  ⚠️  IMPOSSIBLE: {child_name} (child)")
                    print(f"      Parent 1: {parent_genders[0]['name']} ({gender1})")
                    print(f"      Parent 2: {parent_genders[1]['name']} ({gender2})")

                    # Try to fix by correcting roles
                    if gender1 == 'M' and gender2 == 'M':
                        # Both male - one should be mother
                        # Check which name ends in 'a'
                        for pg in parent_genders:
                            parent = self.persons.get(pg['id'])
                            if parent and self.infer_gender_from_name(parent['given_name']) == 'F':
                                # This should be mother!
                                rel = self.relationships[pg['rel_id']]
                                rel['role'] = 'mother'
                                self.stats['relationships_fixed'] += 1
                                print(f"      ✓ Fixed: {pg['name']} role → mother")

                    elif gender1 == 'F' and gender2 == 'F':
                        # Both female - one should be father
                        for pg in parent_genders:
                            parent = self.persons.get(pg['id'])
                            if parent and self.infer_gender_from_name(parent['given_name']) == 'M':
                                # This should be father!
                                rel = self.relationships[pg['rel_id']]
                                rel['role'] = 'father'
                                self.stats['relationships_fixed'] += 1
                                print(f"      ✓ Fixed: {pg['name']} role → father")

        print(f"\n✓ Checked {self.stats['parent_relationships_checked']} children")
        print(f"✓ Found {self.stats['impossible_relationships']} impossible relationships")
        print(f"✓ Fixed {self.stats['relationships_fixed']} relationship roles")

    def validate_birth_events(self):
        """Validate all birth events have correct parents"""
        print("\nValidating birth events...")

        issues = 0
        fixed = 0

        for event_id, event in self.events.items():
            if event.get('type') != 'birth':
                continue

            father_id = event.get('father')
            mother_id = event.get('mother')

            if not father_id or not mother_id:
                continue  # Can't validate

            father = self.persons.get(father_id)
            mother = self.persons.get(mother_id)

            if not father or not mother:
                continue

            father_gender = father.get('gender', 'U')
            mother_gender = mother.get('gender', 'U')

            # Check for issues
            if father_gender == 'F' or mother_gender == 'M':
                issues += 1
                child = self.persons.get(event.get('child'), {})
                print(f"\n  ⚠️  EVENT {event_id}: {child.get('given_name', '')} {child.get('surname', '')}")
                print(f"      Father: {father.get('given_name', '')} ({father_gender})")
                print(f"      Mother: {mother.get('given_name', '')} ({mother_gender})")

                # Try to swap if roles are reversed
                if father_gender == 'F' and mother_gender == 'M':
                    event['father'] = mother_id
                    event['mother'] = father_id
                    fixed += 1
                    print(f"      ✓ Swapped father/mother")

        if issues > 0:
            print(f"\n✓ Found {issues} event issues")
            print(f"✓ Fixed {fixed} events")
        else:
            print("✓ All birth events valid!")

    def generate_report(self):
        """Generate gender distribution report"""
        print("\n" + "=" * 70)
        print("GENDER DISTRIBUTION REPORT")
        print("=" * 70)

        gender_counts = {'M': 0, 'F': 0, 'U': 0}
        for person in self.persons.values():
            gender = person.get('gender', 'U')
            gender_counts[gender] = gender_counts.get(gender, 0) + 1

        total = sum(gender_counts.values())
        print(f"Male (M):    {gender_counts['M']:4d} ({gender_counts['M']/total*100:.1f}%)")
        print(f"Female (F):  {gender_counts['F']:4d} ({gender_counts['F']/total*100:.1f}%)")
        print(f"Unknown (U): {gender_counts['U']:4d} ({gender_counts['U']/total*100:.1f}%)")
        print(f"Total:       {total:4d}")

        # List unknown genders
        if gender_counts['U'] > 0:
            print(f"\nPersons with unknown gender:")
            unknowns = [p for p in self.persons.values() if p.get('gender') == 'U']
            for p in unknowns[:10]:
                print(f"  {p.get('id')}: {p.get('given_name', '')} {p.get('surname', '')}")
            if len(unknowns) > 10:
                print(f"  ... and {len(unknowns)-10} more")

    def export_fixed_data(self, output_file: str):
        """Export fixed data"""
        print(f"\nExporting fixed data to: {output_file}")

        data = {
            'persons': self.persons,
            'events': self.events,
            'relationships': self.relationships,
            'metadata': {
                'total_persons': len(self.persons),
                'total_events': len(self.events),
                'total_relationships': len(self.relationships),
                'gender_fixes': self.stats['gender_fixed'],
                'relationship_fixes': self.stats['relationships_fixed']
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✓ Exported {len(self.persons)} persons")
        print(f"✓ Exported {len(self.events)} events")
        print(f"✓ Exported {len(self.relationships)} relationships")


def main():
    print("=" * 70)
    print("GENDER AND PARENT RELATIONSHIP FIXER")
    print("=" * 70)

    fixer = GenderFixer()
    fixer.load_data('data/genealogy_complete.json')

    # Step 1: Fix all genders based on names
    fixer.fix_all_genders()

    # Step 2: Validate parent relationships
    fixer.validate_parent_relationships()

    # Step 3: Validate birth events
    fixer.validate_birth_events()

    # Step 4: Generate report
    fixer.generate_report()

    # Step 5: Export fixed data
    fixer.export_fixed_data('data/genealogy_fixed.json')

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Gender classifications fixed:    {fixer.stats['gender_fixed']}")
    print(f"Impossible relationships found:  {fixer.stats['impossible_relationships']}")
    print(f"Relationship roles fixed:        {fixer.stats['relationships_fixed']}")
    print("=" * 70)

    print("\n✓ Validation and fixes complete!")
    print("\nTo apply: cp data/genealogy_fixed.json data/genealogy_complete.json")


if __name__ == '__main__':
    main()
