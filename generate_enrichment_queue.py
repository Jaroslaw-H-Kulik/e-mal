#!/usr/bin/env python3
"""
GEDCOM Enrichment Queue Generator

Generates a queue of enrichment candidates for review in the web UI.
For each matched person, finds their parents and children from GEDCOM
and suggests matches with existing persons in base.md.
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class GedcomPerson:
    """Person from GEDCOM"""
    id: str
    given_name: Optional[str] = None
    surname: Optional[str] = None
    maiden_name: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    birth_year: Optional[int] = None
    death_date: Optional[str] = None
    death_year: Optional[int] = None
    family_as_child: Optional[str] = None
    family_as_spouse: List[str] = field(default_factory=list)


@dataclass
class GedcomFamily:
    """Family from GEDCOM"""
    id: str
    husband: Optional[str] = None
    wife: Optional[str] = None
    children: List[str] = field(default_factory=list)


class EnrichmentQueueGenerator:
    """Generate enrichment queue from GEDCOM and base.md data"""

    def __init__(self):
        self.base_persons = {}
        self.base_relationships = {}
        self.gedcom_persons = {}
        self.gedcom_families = {}
        self.matches = {}  # base_id -> gedcom_id
        self.enrichment_queue = []

    def load_base_data(self, filepath: str):
        """Load base.md processed data"""
        print(f"Loading base data: {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.base_persons = data.get('persons', {})
        self.base_relationships = data.get('relationships', {})

        print(f"✓ Loaded {len(self.base_persons)} base persons")
        print(f"✓ Loaded {len(self.base_relationships)} base relationships")

    def load_gedcom(self, filepath: str):
        """Load and parse GEDCOM file"""
        print(f"\nLoading GEDCOM: {filepath}")

        # Try different encodings
        for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
            try:
                with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                    lines = f.readlines()
                print(f"✓ Read with {encoding} encoding")
                break
            except Exception:
                continue
        else:
            raise Exception("Could not read GEDCOM file")

        # Parse GEDCOM
        current_record = None
        current_type = None
        current_tag = None

        for line in lines:
            line = line.rstrip('\n\r')
            if not line.strip():
                continue

            parts = line.split(None, 2)
            if len(parts) < 2:
                continue

            try:
                level = int(parts[0])
            except ValueError:
                continue

            # Handle @ID@ format
            if parts[1].startswith('@') and parts[1].endswith('@'):
                record_id = parts[1]
                tag = parts[2] if len(parts) > 2 else ''
                value = ''
            else:
                tag = parts[1]
                value = parts[2] if len(parts) > 2 else ''
                record_id = None

            # Level 0: New record
            if level == 0:
                # Save previous record
                if current_record:
                    if current_type == 'INDI':
                        self.gedcom_persons[current_record.id] = current_record
                    elif current_type == 'FAM':
                        self.gedcom_families[current_record.id] = current_record

                if tag == 'INDI' and record_id:
                    current_record = GedcomPerson(id=record_id)
                    current_type = 'INDI'
                elif tag == 'FAM' and record_id:
                    current_record = GedcomFamily(id=record_id)
                    current_type = 'FAM'
                else:
                    current_record = None
                    current_type = None
                current_tag = None

            # Level 1: Main tags
            elif level == 1 and current_record:
                current_tag = tag

                if current_type == 'INDI':
                    if tag == 'SEX':
                        current_record.gender = value
                    elif tag == 'FAMC':
                        current_record.family_as_child = value
                    elif tag == 'FAMS':
                        current_record.family_as_spouse.append(value)

                elif current_type == 'FAM':
                    if tag == 'HUSB':
                        current_record.husband = value
                    elif tag == 'WIFE':
                        current_record.wife = value
                    elif tag == 'CHIL':
                        current_record.children.append(value)

            # Level 2: Sub-tags
            elif level == 2 and current_record and current_tag:
                if current_type == 'INDI':
                    if current_tag == 'NAME':
                        if tag == 'GIVN':
                            current_record.given_name = value
                        elif tag == 'SURN':
                            current_record.surname = value
                        elif tag == '_MARNM':
                            current_record.maiden_name = value
                    elif current_tag == 'BIRT':
                        if tag == 'DATE':
                            current_record.birth_date = value
                            current_record.birth_year = self.extract_year(value)
                    elif current_tag == 'DEAT':
                        if tag == 'DATE':
                            current_record.death_date = value
                            current_record.death_year = self.extract_year(value)

        # Save last record
        if current_record:
            if current_type == 'INDI':
                self.gedcom_persons[current_record.id] = current_record
            elif current_type == 'FAM':
                self.gedcom_families[current_record.id] = current_record

        print(f"✓ Parsed {len(self.gedcom_persons)} GEDCOM persons")
        print(f"✓ Parsed {len(self.gedcom_families)} GEDCOM families")

    def extract_year(self, date_str: str) -> Optional[int]:
        """Extract year from GEDCOM date"""
        if not date_str:
            return None
        match = re.search(r'\b(1\d{3}|20\d{2})\b', date_str)
        if match:
            return int(match.group(1))
        return None

    def match_persons(self):
        """Match base persons with GEDCOM persons"""
        print("\nMatching base persons with GEDCOM...")

        for base_id, base_person in self.base_persons.items():
            given_name = base_person.get('given_name', '').lower()
            surname = base_person.get('surname', '').lower()
            birth_year = base_person.get('birth_year_estimate')

            if not given_name or not surname:
                continue

            # Find candidates
            best_match = None
            best_score = 0

            for ged_id, ged_person in self.gedcom_persons.items():
                ged_given = (ged_person.given_name or '').lower()
                ged_surname = (ged_person.surname or '').lower()

                if ged_given == given_name and ged_surname == surname:
                    score = 100

                    # Birth year bonus
                    if birth_year and ged_person.birth_year:
                        diff = abs(birth_year - ged_person.birth_year)
                        if diff == 0:
                            score += 50
                        elif diff <= 2:
                            score += 30
                        elif diff <= 5:
                            score += 10
                        else:
                            score -= 20

                    if score > best_score and score >= 100:
                        best_score = score
                        best_match = ged_id

            if best_match:
                self.matches[base_id] = best_match

        print(f"✓ Matched {len(self.matches)} persons")

    def generate_queue(self):
        """Generate enrichment queue for matched persons"""
        print("\nGenerating enrichment queue...")

        for base_id, ged_id in self.matches.items():
            base_person = self.base_persons[base_id]
            ged_person = self.gedcom_persons[ged_id]

            # Build enrichment entry
            entry = {
                'match_id': f"MATCH_{base_id}_{ged_id}",
                'base_person': {
                    'id': base_id,
                    'name': f"{base_person.get('given_name')} {base_person.get('surname')}",
                    'birth_year': base_person.get('birth_year_estimate'),
                    'death_year': base_person.get('death_year_estimate'),
                    'gender': base_person.get('gender')
                },
                'gedcom_person': {
                    'id': ged_id,
                    'name': f"{ged_person.given_name} {ged_person.surname}",
                    'birth_date': ged_person.birth_date,
                    'birth_year': ged_person.birth_year,
                    'death_date': ged_person.death_date,
                    'death_year': ged_person.death_year,
                    'gender': ged_person.gender
                },
                'confidence': self.calculate_confidence(base_person, ged_person),
                'personal_data_imports': self.get_personal_data_imports(base_person, ged_person),
                'parents': self.get_parent_options(base_id, ged_person),
                'children': self.get_children_options(base_id, ged_person)
            }

            # Only add if there's something to enrich
            if (entry['personal_data_imports'] or
                entry['parents'] or
                entry['children']):
                self.enrichment_queue.append(entry)

        print(f"✓ Generated {len(self.enrichment_queue)} enrichment entries")

    def calculate_confidence(self, base_person, ged_person) -> int:
        """Calculate match confidence score"""
        score = 100  # Base for name match

        birth_year_base = base_person.get('birth_year_estimate')
        birth_year_ged = ged_person.birth_year

        if birth_year_base and birth_year_ged:
            diff = abs(birth_year_base - birth_year_ged)
            if diff == 0:
                score += 50
            elif diff <= 2:
                score += 30
            elif diff <= 5:
                score += 10

        return min(score, 100)

    def get_personal_data_imports(self, base_person, ged_person) -> Dict:
        """Get personal data that can be imported"""
        imports = {}

        # Birth date
        if not base_person.get('birth_year_estimate') and ged_person.birth_year:
            imports['birth_year'] = ged_person.birth_year
            if ged_person.birth_date:
                imports['birth_date'] = ged_person.birth_date

        # Death date
        if not base_person.get('death_year_estimate') and ged_person.death_year:
            imports['death_year'] = ged_person.death_year
            if ged_person.death_date:
                imports['death_date'] = ged_person.death_date

        return imports

    def get_parent_options(self, base_id, ged_person) -> List[Dict]:
        """Get parent import options with match candidates"""
        parents = []

        if not ged_person.family_as_child:
            return parents

        family = self.gedcom_families.get(ged_person.family_as_child)
        if not family:
            return parents

        # Father
        if family.husband:
            father = self.gedcom_persons.get(family.husband)
            if father and father.given_name:
                parent_entry = self.build_parent_entry(father, 'father', base_id)
                if parent_entry:
                    parents.append(parent_entry)

        # Mother
        if family.wife:
            mother = self.gedcom_persons.get(family.wife)
            if mother and mother.given_name:
                parent_entry = self.build_parent_entry(mother, 'mother', base_id)
                if parent_entry:
                    parents.append(parent_entry)

        return parents

    def build_parent_entry(self, ged_parent, relationship, child_base_id) -> Optional[Dict]:
        """Build parent entry with match candidates"""
        # Check if already has this parent
        existing_parent = self.get_existing_parent(child_base_id, relationship)
        if existing_parent:
            return None  # Already has this parent

        # Find potential matches
        matches = self.find_parent_matches(ged_parent, child_base_id)

        # Generate new ID for "create new" option
        max_id = max([int(p['id'][1:]) for p in self.base_persons.values()], default=0)
        new_id = f"P{(max_id + 1):04d}"

        return {
            'gedcom_id': ged_parent.id,
            'given_name': ged_parent.given_name,
            'surname': ged_parent.surname,
            'maiden_name': ged_parent.maiden_name,
            'birth_year': ged_parent.birth_year,
            'death_year': ged_parent.death_year,
            'gender': ged_parent.gender,
            'relationship': relationship,
            'matches': matches,
            'create_new_option': {
                'would_create_id': new_id,
                'would_add_relationship': f"biological_parent ({relationship})"
            }
        }

    def find_parent_matches(self, ged_parent, child_base_id) -> List[Dict]:
        """Find potential matches for a parent in base data"""
        candidates = []
        child = self.base_persons[child_base_id]
        child_birth_year = child.get('birth_year_estimate')

        for person_id, person in self.base_persons.items():
            score = 0
            evidence = []

            # Name match (required)
            if not self.names_match(ged_parent, person):
                continue

            score += 50
            evidence.append("Name matches")

            # Birth year consistency (parent should be 15-60 years older)
            if child_birth_year and person.get('birth_year_estimate'):
                age_diff = child_birth_year - person.get('birth_year_estimate')
                if 15 <= age_diff <= 60:
                    score += 20
                    evidence.append(f"Age difference consistent ({age_diff} years)")
                elif 10 <= age_diff <= 70:
                    score += 10
                    evidence.append(f"Age difference plausible ({age_diff} years)")

            # Already parent of siblings?
            if self.is_parent_of_siblings(person_id, child_base_id):
                score += 30
                evidence.append("Already parent of this person's siblings")

            # Gender matches
            if person.get('gender') == ged_parent.gender:
                score += 10
                evidence.append("Gender matches")

            # Death year similar
            if (ged_parent.death_year and person.get('death_year_estimate') and
                abs(ged_parent.death_year - person.get('death_year_estimate')) <= 5):
                score += 10
                evidence.append("Death year matches")

            if score >= 60:
                candidates.append({
                    'person_id': person_id,
                    'score': score,
                    'recommended': score >= 85,
                    'evidence': evidence,
                    'would_add': self.calculate_would_add(person, ged_parent),
                    'conflicts': []
                })

        return sorted(candidates, key=lambda x: x['score'], reverse=True)

    def get_children_options(self, base_id, ged_person) -> List[Dict]:
        """Get children import options with match candidates"""
        children = []

        for family_id in ged_person.family_as_spouse:
            family = self.gedcom_families.get(family_id)
            if not family:
                continue

            for child_ged_id in family.children:
                child_ged = self.gedcom_persons.get(child_ged_id)
                if not child_ged or not child_ged.given_name:
                    continue

                # Check if already has this child
                if self.is_existing_child(base_id, child_ged):
                    continue

                child_entry = self.build_child_entry(child_ged, base_id)
                if child_entry:
                    children.append(child_entry)

        return children

    def build_child_entry(self, ged_child, parent_base_id) -> Optional[Dict]:
        """Build child entry with match candidates"""
        # Find potential matches
        matches = self.find_child_matches(ged_child, parent_base_id)

        # Generate new ID
        max_id = max([int(p['id'][1:]) for p in self.base_persons.values()], default=0)
        new_id = f"P{(max_id + 1):04d}"

        return {
            'gedcom_id': ged_child.id,
            'given_name': ged_child.given_name,
            'surname': ged_child.surname,
            'birth_year': ged_child.birth_year,
            'death_year': ged_child.death_year,
            'gender': ged_child.gender,
            'matches': matches,
            'create_new_option': {
                'would_create_id': new_id,
                'would_add_relationship': "biological_parent (child)"
            }
        }

    def find_child_matches(self, ged_child, parent_base_id) -> List[Dict]:
        """Find potential matches for a child in base data"""
        candidates = []
        parent = self.base_persons[parent_base_id]

        for person_id, person in self.base_persons.items():
            score = 0
            evidence = []

            # Name match (required)
            if not self.names_match(ged_child, person):
                continue

            score += 50
            evidence.append("Name matches")

            # Birth year close
            if ged_child.birth_year and person.get('birth_year_estimate'):
                diff = abs(ged_child.birth_year - person.get('birth_year_estimate'))
                if diff == 0:
                    score += 30
                    evidence.append("Birth year exact match")
                elif diff <= 2:
                    score += 20
                    evidence.append(f"Birth year close ({diff} years)")
                elif diff <= 5:
                    score += 10
                    evidence.append(f"Birth year similar ({diff} years)")

            # Already child of this parent?
            if self.is_child_of(person_id, parent_base_id):
                score += 30
                evidence.append("Already child of this parent")

            # Gender matches
            if person.get('gender') == ged_child.gender:
                score += 10
                evidence.append("Gender matches")

            if score >= 60:
                candidates.append({
                    'person_id': person_id,
                    'score': score,
                    'recommended': score >= 85,
                    'evidence': evidence,
                    'would_add': self.calculate_would_add(person, ged_child),
                    'conflicts': []
                })

        return sorted(candidates, key=lambda x: x['score'], reverse=True)

    def names_match(self, ged_person, base_person) -> bool:
        """Check if names match"""
        ged_given = (ged_person.given_name or '').lower()
        ged_surname = (ged_person.surname or '').lower()
        base_given = base_person.get('given_name', '').lower()
        base_surname = base_person.get('surname', '').lower()

        return ged_given == base_given and ged_surname == base_surname

    def calculate_would_add(self, base_person, ged_person) -> List[str]:
        """Calculate what data would be added"""
        additions = []

        if not base_person.get('birth_year_estimate') and ged_person.birth_year:
            additions.append(f"birth_year: {ged_person.birth_year}")

        if not base_person.get('death_year_estimate') and ged_person.death_year:
            additions.append(f"death_year: {ged_person.death_year}")

        return additions

    def get_existing_parent(self, child_id, role) -> Optional[str]:
        """Check if child already has a parent with this role"""
        for rel in self.base_relationships.values():
            if (rel['type'] == 'biological_parent' and
                rel['to_person'] == child_id and
                rel.get('role') == role):
                return rel['from_person']
        return None

    def is_parent_of_siblings(self, person_id, child_id) -> bool:
        """Check if person is parent of child's siblings"""
        # Get child's parents
        child_parents = []
        for rel in self.base_relationships.values():
            if rel['type'] == 'biological_parent' and rel['to_person'] == child_id:
                child_parents.append(rel['from_person'])

        if not child_parents:
            return False

        # Check if person is parent of children of those parents
        for rel in self.base_relationships.values():
            if (rel['type'] == 'biological_parent' and
                rel['from_person'] == person_id and
                rel['to_person'] != child_id):
                # Check if this child has same parents
                other_child_parents = []
                for r in self.base_relationships.values():
                    if r['type'] == 'biological_parent' and r['to_person'] == rel['to_person']:
                        other_child_parents.append(r['from_person'])

                if any(p in child_parents for p in other_child_parents):
                    return True

        return False

    def is_child_of(self, person_id, parent_id) -> bool:
        """Check if person is child of parent"""
        for rel in self.base_relationships.values():
            if (rel['type'] == 'biological_parent' and
                rel['from_person'] == parent_id and
                rel['to_person'] == person_id):
                return True
        return False

    def is_existing_child(self, parent_id, ged_child) -> bool:
        """Check if parent already has this child"""
        for rel in self.base_relationships.values():
            if rel['type'] == 'biological_parent' and rel['from_person'] == parent_id:
                child = self.base_persons.get(rel['to_person'])
                if child and self.names_match(ged_child, child):
                    return True
        return False

    def save_queue(self, filepath: str):
        """Save enrichment queue to file"""
        print(f"\nSaving enrichment queue to: {filepath}")

        queue_data = {
            'generated': True,
            'total_matches': len(self.enrichment_queue),
            'matches': self.enrichment_queue,
            'stats': {
                'base_persons': len(self.base_persons),
                'gedcom_persons': len(self.gedcom_persons),
                'matched_persons': len(self.matches),
                'enrichment_candidates': len(self.enrichment_queue)
            }
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(queue_data, f, ensure_ascii=False, indent=2)

        print(f"✓ Saved {len(self.enrichment_queue)} enrichment entries")

        # Print summary
        total_parents = sum(len(e['parents']) for e in self.enrichment_queue)
        total_children = sum(len(e['children']) for e in self.enrichment_queue)

        print(f"\n{'='*70}")
        print("ENRICHMENT QUEUE SUMMARY")
        print(f"{'='*70}")
        print(f"Total matched persons: {len(self.enrichment_queue)}")
        print(f"Total parents to review: {total_parents}")
        print(f"Total children to review: {total_children}")
        print(f"{'='*70}")


def main():
    print("="*70)
    print("GEDCOM ENRICHMENT QUEUE GENERATOR")
    print("="*70)

    generator = EnrichmentQueueGenerator()

    # Load data
    generator.load_base_data('data/genealogy_complete.json')
    generator.load_gedcom('base.ged')

    # Match and generate queue
    generator.match_persons()
    generator.generate_queue()

    # Save
    generator.save_queue('data/enrichment_queue.json')

    print("\n✓ Queue generation complete!")
    print("\nNext steps:")
    print("1. Open web interface")
    print("2. Click 'Review GEDCOM Matches'")
    print("3. Review and approve enrichments")


if __name__ == '__main__':
    main()
