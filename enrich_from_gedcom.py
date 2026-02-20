#!/usr/bin/env python3
"""
GEDCOM Data Enrichment Tool

Enriches persons.json with data from base.ged (MyHeritage export):
- Birth dates, death dates
- Parents, children (no grandchildren)
- New persons and relationships
"""

import json
import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set
from collections import defaultdict


@dataclass
class GedcomIndividual:
    """Person from GEDCOM file"""
    id: str
    given_name: Optional[str] = None
    surname: Optional[str] = None
    maiden_name: Optional[str] = None
    gender: Optional[str] = None  # M, F, or None
    birth_date: Optional[str] = None
    birth_year: Optional[int] = None
    birth_place: Optional[str] = None
    death_date: Optional[str] = None
    death_year: Optional[int] = None
    death_place: Optional[str] = None
    family_as_spouse: List[str] = field(default_factory=list)  # FAMS - family IDs
    family_as_child: Optional[str] = None  # FAMC - family ID


@dataclass
class GedcomFamily:
    """Family from GEDCOM file"""
    id: str
    husband: Optional[str] = None
    wife: Optional[str] = None
    children: List[str] = field(default_factory=list)
    marriage_date: Optional[str] = None
    marriage_place: Optional[str] = None


class GedcomParser:
    """Parse GEDCOM 5.5.1 format"""

    def __init__(self):
        self.individuals: Dict[str, GedcomIndividual] = {}
        self.families: Dict[str, GedcomFamily] = {}

    def parse_file(self, filepath: str):
        """Parse GEDCOM file"""
        print(f"Parsing GEDCOM file: {filepath}")

        # Try different encodings
        for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
            try:
                with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                    lines = f.readlines()
                print(f"✓ Successfully read with {encoding} encoding")
                break
            except Exception as e:
                continue
        else:
            raise Exception("Could not read GEDCOM file with any known encoding")

        current_record = None
        current_type = None
        current_tag = None

        for line in lines:
            line = line.rstrip('\n\r')
            if not line.strip():
                continue

            # Parse line: level TAG [value] or level @ID@ TAG
            parts = line.split(None, 2)
            if len(parts) < 2:
                continue

            # Skip lines that don't start with a valid level number
            try:
                level = int(parts[0])
            except ValueError:
                continue  # Skip malformed lines

            # Handle @ID@ format
            if parts[1].startswith('@') and parts[1].endswith('@'):
                record_id = parts[1]
                tag = parts[2] if len(parts) > 2 else ''
                value = ''
            else:
                tag = parts[1]
                value = parts[2] if len(parts) > 2 else ''

            # Level 0: New record
            if level == 0:
                if tag == 'INDI' and record_id:
                    current_record = GedcomIndividual(id=record_id)
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
                        elif tag == 'PLAC':
                            current_record.birth_place = value
                    elif current_tag == 'DEAT':
                        if tag == 'DATE':
                            current_record.death_date = value
                            current_record.death_year = self.extract_year(value)
                        elif tag == 'PLAC':
                            current_record.death_place = value

                elif current_type == 'FAM':
                    if current_tag == 'MARR':
                        if tag == 'DATE':
                            current_record.marriage_date = value
                        elif tag == 'PLAC':
                            current_record.marriage_place = value

            # Save completed records
            if level == 0 and current_record:
                if current_type == 'INDI':
                    self.individuals[current_record.id] = current_record
                elif current_type == 'FAM':
                    self.families[current_record.id] = current_record

        # Save last record
        if current_record:
            if current_type == 'INDI':
                self.individuals[current_record.id] = current_record
            elif current_type == 'FAM':
                self.families[current_record.id] = current_record

        print(f"✓ Parsed {len(self.individuals)} individuals")
        print(f"✓ Parsed {len(self.families)} families")

    def extract_year(self, date_str: str) -> Optional[int]:
        """Extract year from GEDCOM date format"""
        if not date_str:
            return None
        # Try to find 4-digit year
        match = re.search(r'\b(1\d{3}|20\d{2})\b', date_str)
        if match:
            return int(match.group(1))
        return None


class DataEnricher:
    """Enrich persons.json with GEDCOM data"""

    def __init__(self, gedcom_parser: GedcomParser):
        self.gedcom = gedcom_parser
        self.persons = {}
        self.events = {}
        self.relationships = {}
        self.matches = {}  # Maps person_id to gedcom_id
        self.new_person_counter = 0
        self.stats = {
            'matched': 0,
            'enriched_birth': 0,
            'enriched_death': 0,
            'added_parents': 0,
            'added_children': 0,
            'added_persons': 0,
            'added_relationships': 0
        }

    def load_current_data(self, data_file: str):
        """Load current persons.json"""
        print(f"\nLoading current data: {data_file}")
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.persons = data.get('persons', {})
        self.events = data.get('events', {})
        self.relationships = data.get('relationships', {})

        print(f"✓ Loaded {len(self.persons)} persons")
        print(f"✓ Loaded {len(self.events)} events")
        print(f"✓ Loaded {len(self.relationships)} relationships")

    def match_persons(self):
        """Match persons.json entries with GEDCOM individuals"""
        print("\nMatching persons with GEDCOM data...")

        for person_id, person in self.persons.items():
            given_name = person.get('given_name', '').lower()
            surname = person.get('surname', '').lower()
            birth_year = person.get('birth_year_estimate')

            if not given_name or not surname:
                continue

            # Find candidates in GEDCOM
            candidates = []
            for ged_id, ged_person in self.gedcom.individuals.items():
                ged_given = (ged_person.given_name or '').lower()
                ged_surname = (ged_person.surname or '').lower()

                # Name match
                if ged_given == given_name and ged_surname == surname:
                    score = 100

                    # Boost score for birth year match
                    if birth_year and ged_person.birth_year:
                        year_diff = abs(birth_year - ged_person.birth_year)
                        if year_diff == 0:
                            score += 50
                        elif year_diff <= 2:
                            score += 30
                        elif year_diff <= 5:
                            score += 10
                        else:
                            score -= 20

                    candidates.append((ged_id, score))

            # Pick best match
            if candidates:
                candidates.sort(key=lambda x: x[1], reverse=True)
                best_match, best_score = candidates[0]

                if best_score >= 100:  # Only accept good matches
                    self.matches[person_id] = best_match
                    self.stats['matched'] += 1

        print(f"✓ Matched {self.stats['matched']} persons")

    def enrich_data(self):
        """Enrich matched persons with GEDCOM data"""
        print("\nEnriching data...")

        # Use list() to create a copy to avoid RuntimeError
        for person_id, ged_id in list(self.matches.items()):
            person = self.persons[person_id]
            ged_person = self.gedcom.individuals[ged_id]

            # Enrich birth information
            if not person.get('birth_year_estimate') and ged_person.birth_year:
                person['birth_year_estimate'] = ged_person.birth_year
                self.stats['enriched_birth'] += 1

            # Enrich death information
            if not person.get('death_year_estimate') and ged_person.death_year:
                person['death_year_estimate'] = ged_person.death_year
                self.stats['enriched_death'] += 1

            # Add maiden name if missing
            if not person.get('maiden_name') and ged_person.maiden_name:
                person['maiden_name'] = ged_person.maiden_name

            # Add parents (from FAMC - family as child)
            if ged_person.family_as_child:
                self.add_parents(person_id, ged_person.family_as_child)

            # Add children (from FAMS - families as spouse)
            for family_id in ged_person.family_as_spouse:
                self.add_children(person_id, family_id)

        print(f"✓ Enriched {self.stats['enriched_birth']} birth dates")
        print(f"✓ Enriched {self.stats['enriched_death']} death dates")
        print(f"✓ Added {self.stats['added_parents']} parent relationships")
        print(f"✓ Added {self.stats['added_children']} child relationships")

    def add_parents(self, person_id: str, family_id: str):
        """Add parent relationships"""
        family = self.gedcom.families.get(family_id)
        if not family:
            return

        # Add father
        if family.husband:
            father_person_id = self.get_or_create_person(family.husband)
            if father_person_id:
                self.add_relationship('biological_parent', father_person_id, person_id, 'father')
                self.stats['added_parents'] += 1

        # Add mother
        if family.wife:
            mother_person_id = self.get_or_create_person(family.wife)
            if mother_person_id:
                self.add_relationship('biological_parent', mother_person_id, person_id, 'mother')
                self.stats['added_parents'] += 1

    def add_children(self, person_id: str, family_id: str):
        """Add children (direct children only, no grandchildren)"""
        family = self.gedcom.families.get(family_id)
        if not family:
            return

        for child_ged_id in family.children:
            child_person_id = self.get_or_create_person(child_ged_id)
            if child_person_id and child_person_id != person_id:
                # Determine role based on gender
                person = self.persons.get(person_id, {})
                role = 'father' if person.get('gender') == 'M' else 'mother'
                self.add_relationship('biological_parent', person_id, child_person_id, role)
                self.stats['added_children'] += 1

    def get_or_create_person(self, ged_id: str) -> Optional[str]:
        """Get existing person ID or create new person from GEDCOM"""
        # Check if already matched
        for person_id, matched_ged_id in self.matches.items():
            if matched_ged_id == ged_id:
                return person_id

        # Create new person
        ged_person = self.gedcom.individuals.get(ged_id)
        if not ged_person or not ged_person.given_name:
            return None

        # Generate new person ID
        self.new_person_counter += 1
        new_person_id = f"P{(5000 + self.new_person_counter):04d}"

        # Create person record
        new_person = {
            'id': new_person_id,
            'given_name': ged_person.given_name,
            'surname': ged_person.surname or 'Unknown',
            'gender': ged_person.gender or 'U',
            'confidence': 'high',
            'data_quality': 'from_gedcom'
        }

        if ged_person.maiden_name:
            new_person['maiden_name'] = ged_person.maiden_name
        if ged_person.birth_year:
            new_person['birth_year_estimate'] = ged_person.birth_year
        if ged_person.death_year:
            new_person['death_year_estimate'] = ged_person.death_year

        self.persons[new_person_id] = new_person
        self.matches[new_person_id] = ged_id  # Track the match
        self.stats['added_persons'] += 1

        return new_person_id

    def add_relationship(self, rel_type: str, from_id: str, to_id: str, role: str):
        """Add relationship if it doesn't exist"""
        # Check if relationship already exists
        for rel in self.relationships.values():
            if (rel['type'] == rel_type and
                rel['from_person'] == from_id and
                rel['to_person'] == to_id):
                return  # Already exists

        # Create new relationship
        rel_id = f"R{(len(self.relationships) + 1):04d}"
        self.relationships[rel_id] = {
            'id': rel_id,
            'type': rel_type,
            'from_person': from_id,
            'to_person': to_id,
            'role': role,
            'evidence': ['gedcom_import']
        }
        self.stats['added_relationships'] += 1

    def export_enriched_data(self, output_file: str):
        """Export enriched data"""
        print(f"\nExporting enriched data to: {output_file}")

        enriched_data = {
            'persons': self.persons,
            'events': self.events,
            'relationships': self.relationships,
            'metadata': {
                'total_persons': len(self.persons),
                'total_events': len(self.events),
                'total_relationships': len(self.relationships),
                'enriched_from_gedcom': True,
                'enrichment_date': datetime.now().isoformat(),
                'enrichment_stats': self.stats
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enriched_data, f, ensure_ascii=False, indent=2)

        print(f"✓ Exported {len(self.persons)} persons")
        print(f"✓ Exported {len(self.events)} events")
        print(f"✓ Exported {len(self.relationships)} relationships")

    def print_summary(self):
        """Print enrichment summary"""
        print("\n" + "=" * 70)
        print("ENRICHMENT SUMMARY")
        print("=" * 70)
        print(f"Matched persons:           {self.stats['matched']}")
        print(f"Added birth dates:         {self.stats['enriched_birth']}")
        print(f"Added death dates:         {self.stats['enriched_death']}")
        print(f"Added parent relationships: {self.stats['added_parents']}")
        print(f"Added child relationships:  {self.stats['added_children']}")
        print(f"Added new persons:         {self.stats['added_persons']}")
        print(f"Added relationships:       {self.stats['added_relationships']}")
        print("=" * 70)


def main():
    print("=" * 70)
    print("GEDCOM DATA ENRICHMENT TOOL")
    print("=" * 70)

    # Parse GEDCOM
    parser = GedcomParser()
    parser.parse_file('base.ged')

    # Enrich data
    enricher = DataEnricher(parser)
    enricher.load_current_data('data/genealogy_complete.json')
    enricher.match_persons()
    enricher.enrich_data()

    # Export
    enricher.export_enriched_data('data/genealogy_enriched.json')
    enricher.print_summary()

    print("\n✓ Enrichment complete!")
    print("Review: data/genealogy_enriched.json")
    print("To use: cp data/genealogy_enriched.json data/genealogy_complete.json")


if __name__ == '__main__':
    main()
