#!/usr/bin/env python3
"""
Genealogical Data Parser V2 - Corrected Format Understanding

Key rules from base.md explanation:
1. Birth: Child's surname comes from FATHER
2. Mother's current surname is husband's surname (shown as "z d. [maiden name]")
3. Initials (K.Ł.) refer to person already mentioned in the line
4. św: = witnesses, chrz. = godparents, Ur: = child
5. Death: św: [witnesses] comes FIRST, deceased comes AFTER
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
from collections import defaultdict


@dataclass
class Person:
    id: str
    given_name: str
    surname: str
    maiden_name: Optional[str] = None
    gender: str = "U"
    birth_year_estimate: Optional[int] = None
    death_year_estimate: Optional[int] = None
    occupations: List[str] = field(default_factory=list)
    confidence: str = "medium"

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v not in [None, [], ""]}


@dataclass
class Event:
    id: str
    type: str
    year: int
    date_day: Optional[int] = None
    date_month: Optional[int] = None
    house_number: Optional[str] = None
    original_text: str = ""
    source_line: int = 0
    child: Optional[str] = None
    father: Optional[str] = None
    mother: Optional[str] = None
    mother_maiden_name: Optional[str] = None
    deceased: Optional[str] = None
    age_at_death: Optional[int] = None
    witnesses: List[str] = field(default_factory=list)
    godparents: List[str] = field(default_factory=list)
    groom: Optional[str] = None
    bride: Optional[str] = None

    def to_dict(self):
        d = asdict(self)
        # Remove empty lists and None values
        return {k: v for k, v in d.items() if v not in [None, [], ""]}


@dataclass
class Relationship:
    id: str
    type: str
    from_person: str
    to_person: str
    role: Optional[str] = None
    evidence: List[str] = field(default_factory=list)

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v not in [None, []]}


class GenealogyParserV2:
    def __init__(self, corrections_file=None, merge_log_file=None):
        self.persons = {}
        self.events = {}
        self.relationships = {}
        self.person_counter = 0
        self.event_counter = 0
        self.relationship_counter = 0
        self.current_year = None
        self.current_section = None

        # For tracking person mentions within a line
        self.line_person_map = {}

        # Track uncertain gender classifications
        self.gender_uncertainties = []

        # Load gender corrections if provided
        self.gender_corrections = {}
        if corrections_file:
            self.load_gender_corrections(corrections_file)

        # Load merge log if provided
        self.merge_log = []
        if merge_log_file:
            self.load_merge_log(merge_log_file)

    def load_gender_corrections(self, filepath: str):
        """Load user corrections from gender_review.json"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            corrections_count = 0
            for item in data.get('classifications', []):
                if 'corrected_gender' in item:
                    # Key format: "given_name|surname" for unique identification
                    key = f"{item['given_name']}|{item['surname']}"
                    self.gender_corrections[key] = item['corrected_gender']
                    corrections_count += 1

            if corrections_count > 0:
                print(f"✓ Loaded {corrections_count} gender corrections from {filepath}")
        except FileNotFoundError:
            pass  # No corrections file yet, that's okay

    def load_merge_log(self, filepath: str):
        """Load merge log to auto-apply known merges"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.merge_log = data.get('merges', [])

            if len(self.merge_log) > 0:
                print(f"✓ Loaded {len(self.merge_log)} merge records from {filepath}")
                print("  These duplicates will be automatically merged after parsing")
        except FileNotFoundError:
            pass  # No merge log yet, that's okay

    def apply_merges_from_log(self):
        """Apply known merges from log file to avoid duplicates"""
        print("\nApplying known merges...")
        merges_applied = 0

        for merge_record in self.merge_log:
            kept_name = merge_record['kept_name']
            merged_name = merge_record['merged_name']

            # Find persons matching these names
            kept_id = None
            merged_id = None

            for pid, person in self.persons.items():
                full_name = f"{person.given_name} {person.surname}"
                if full_name == kept_name and kept_id is None:
                    kept_id = pid
                elif full_name == merged_name and merged_id is None:
                    merged_id = pid

            # If both found, apply merge
            if kept_id and merged_id and kept_id != merged_id:
                print(f"  Merging {merged_name} ({merged_id}) → {kept_name} ({kept_id})")

                # Update all relationships
                for rel in self.relationships.values():
                    if rel.from_person == merged_id:
                        rel.from_person = kept_id
                    if rel.to_person == merged_id:
                        rel.to_person = kept_id

                # Update all events
                for event in self.events.values():
                    for field in ['child', 'father', 'mother', 'deceased', 'groom', 'bride']:
                        if hasattr(event, field) and getattr(event, field) == merged_id:
                            setattr(event, field, kept_id)

                    for field in ['witnesses', 'godparents']:
                        if hasattr(event, field):
                            field_value = getattr(event, field)
                            if field_value:
                                setattr(event, field, [kept_id if pid == merged_id else pid for pid in field_value])

                # Remove the merged person
                del self.persons[merged_id]
                merges_applied += 1

            elif not kept_id:
                print(f"  ⚠ Could not find person: {kept_name}")
            elif not merged_id:
                print(f"  ⚠ Could not find person: {merged_name}")

        if merges_applied > 0:
            print(f"✓ Applied {merges_applied} merges from log\n")

    def parse_file(self, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Skip explanation lines (lines 1-13)
        start_line = 0
        for i, line in enumerate(lines):
            if re.match(r'^\d{4}$', line.strip()):
                start_line = i
                break

        for line_num, line in enumerate(lines[start_line:], start=start_line + 1):
            line = line.strip()
            if not line:
                continue

            # Year marker
            if re.match(r'^\d{4}:?$', line):
                self.current_year = int(line.rstrip(':'))
                self.current_section = None
                continue

            # Section marker
            if line.lower() in ['narodziny:', 'zejścia:', 'śluby:', 'urodzenia:']:
                self.current_section = line.rstrip(':').lower()
                continue

            # Skip "Świadkowie:" lines (redundant)
            if line.startswith('Świadkowie:'):
                continue

            # Parse event lines
            if self.current_year:
                if self.current_section in ['narodziny', 'urodzenia'] or (not self.current_section and ' i ' in line and 'Ur' in line):
                    self.parse_birth_line(line, line_num)
                elif self.current_section == 'zejścia' or (not self.current_section and line.startswith('św') and 'Ur' not in line):
                    self.parse_death_line(line, line_num)
                elif self.current_section == 'śluby':
                    self.parse_marriage_line(line, line_num)

        # Apply known merges after parsing
        if self.merge_log:
            self.apply_merges_from_log()

    def parse_birth_line(self, line: str, line_num: int):
        """Parse birth record following the correct format"""
        self.line_person_map = {}  # Reset for each line

        event_id = self.get_next_event_id()

        # Extract house number
        house_match = re.search(r'dom\s+(\d+[a-z]?|\?)', line, re.IGNORECASE)
        house_number = house_match.group(1) if house_match else None

        # Extract date if present (dd.mm format)
        date_match = re.search(r'\((\d{1,2})\.(\d{1,2})\)', line)
        date_day = int(date_match.group(1)) if date_match else None
        date_month = int(date_match.group(2)) if date_match else None

        # Parse: Father i Mother z d. [maiden name]
        parents_pattern = r'^([^:]+?)\s+i\s+([^:,]+?)(?:\s+z\s+d\.?\s+([^:,]+?))?(?::|,)'
        parents_match = re.search(parents_pattern, line)

        father_name = None
        father_age = None
        mother_given_name = None
        mother_maiden_name = None

        if parents_match:
            father_text = parents_match.group(1).strip()
            mother_text = parents_match.group(2).strip()
            mother_maiden_name = parents_match.group(3).strip() if parents_match.group(3) else None

            # Parse father: "Name Surname (age)" or "Name Surname"
            father_match = re.match(r'([A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+)\s+([A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+)(?:\s+\((\d+)[^\)]*\))?', father_text)
            if father_match:
                father_given = father_match.group(1)
                father_surname = father_match.group(2)
                father_age = int(father_match.group(3)) if father_match.group(3) else None
                father_name = (father_given, father_surname)

            # Parse mother: "Name Surname" or "Name"
            mother_match = re.match(r'([A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+)(?:\s+([A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+))?', mother_text)
            if mother_match:
                mother_given_name = mother_match.group(1)

        # Extract witnesses (św:)
        witnesses = []
        witness_match = re.search(r'św:\s*([^-]+?)(?:\s*-\s*chrz|$)', line, re.IGNORECASE)
        if witness_match:
            witness_text = witness_match.group(1).strip()
            witnesses = self.parse_person_list(witness_text)

        # Extract godparents (chrz.)
        godparents = []
        godparent_match = re.search(r'chrz\.?\s+([^.]+?)(?:\.\s*[Uu]r[:.\s]|$)', line, re.IGNORECASE)
        if godparent_match:
            godparent_text = godparent_match.group(1).strip()
            godparents = self.parse_person_list_with_initials(godparent_text)

        # Extract child (Ur: or ur.)
        child_name = None
        child_match = re.search(r'[Uu]r[:.\s]+([A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+(?:\s+[A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+)?)', line)
        if child_match:
            child_name = child_match.group(1).strip()

        # Create persons
        father_id = None
        mother_id = None
        child_id = None

        if father_name:
            father_given, father_surname = father_name
            father_birth_year = self.current_year - father_age if father_age else None
            father_id = self.find_or_create_person(
                father_given, father_surname,
                gender="M",
                birth_year=father_birth_year,
                year_context=self.current_year
            )
            self.line_person_map[f"{father_given[0]}.{father_surname[0]}."] = father_id
            self.line_person_map[f"{father_given} {father_surname}"] = father_id

        if mother_given_name and father_name:
            # Mother takes father's surname
            mother_surname = father_name[1]
            mother_id = self.find_or_create_person(
                mother_given_name, mother_surname,
                gender="F",
                maiden_name=mother_maiden_name,
                year_context=self.current_year
            )
            self.line_person_map[f"{mother_given_name} {mother_surname}"] = mother_id

        if child_name and father_name:
            # Child takes father's surname
            child_parts = child_name.split()
            if len(child_parts) == 1:
                child_given = child_parts[0]
                child_surname = father_name[1]  # Take father's surname
            else:
                child_given = child_parts[0]
                child_surname = child_parts[1]

            child_id = self.find_or_create_person(
                child_given, child_surname,
                gender="U",
                birth_year=self.current_year,
                year_context=self.current_year
            )

        # Create witness and godparent persons
        witness_ids = [self.create_person_from_mention(w) for w in witnesses]
        godparent_ids = [self.create_person_from_mention(g) for g in godparents]

        # Create event
        event = Event(
            id=event_id,
            type="birth",
            year=self.current_year,
            date_day=date_day,
            date_month=date_month,
            house_number=house_number,
            original_text=line,
            source_line=line_num,
            child=child_id,
            father=father_id,
            mother=mother_id,
            mother_maiden_name=mother_maiden_name,
            witnesses=witness_ids,
            godparents=godparent_ids
        )

        self.events[event_id] = event

        # Create relationships
        if father_id and child_id:
            self.add_relationship("biological_parent", father_id, child_id, "father", [event_id])
        if mother_id and child_id:
            self.add_relationship("biological_parent", mother_id, child_id, "mother", [event_id])

        # Add marriage relationship (Catholic records - having children implies marriage)
        if father_id and mother_id:
            self.add_relationship("marriage", father_id, mother_id, "spouse", [event_id])

        for gp_id in godparent_ids:
            if child_id and gp_id:
                self.add_relationship("godparent", gp_id, child_id, "godparent", [event_id])

    def parse_death_line(self, line: str, line_num: int):
        """Parse death record: św: [witnesses], Deceased (age, info), dom X (date)"""
        event_id = self.get_next_event_id()

        # Extract house number
        house_match = re.search(r'dom\s+(\d+[a-z]?|\?)', line, re.IGNORECASE)
        house_number = house_match.group(1) if house_match else None

        # Extract date (dd.mm)
        date_match = re.search(r'\((\d{1,2})\.(\d{1,2})\)', line)
        date_day = int(date_match.group(1)) if date_match else None
        date_month = int(date_match.group(2)) if date_match else None

        # Extract witnesses (św:)
        witnesses = []
        witness_match = re.match(r'^[Śś]w[:.]\s*([^,]+),', line)
        if witness_match:
            witness_text = witness_match.group(1).strip()
            witnesses = self.parse_person_list(witness_text)

        # Extract deceased (after witnesses, before dom or date)
        deceased_match = re.search(r',\s+([A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+\s+[A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+)(?:\s+\(([^\)]+)\))?', line)

        deceased_name = None
        deceased_age = None

        if deceased_match:
            deceased_name = deceased_match.group(1).strip()
            if deceased_match.group(2):
                age_info = deceased_match.group(2)
                age_num = re.search(r'(\d+)\s*(?:lat|rok|miesię|tygodn|dni)', age_info)
                if age_num:
                    deceased_age = int(age_num.group(1))

        # Create persons
        deceased_id = None
        if deceased_name:
            name_parts = deceased_name.split()
            if len(name_parts) >= 2:
                deceased_birth_year = self.current_year - deceased_age if deceased_age else None
                deceased_id = self.find_or_create_person(
                    name_parts[0], name_parts[1],
                    gender="U",
                    birth_year=deceased_birth_year,
                    death_year=self.current_year,
                    year_context=self.current_year
                )

        witness_ids = [self.create_person_from_mention(w) for w in witnesses]

        # Create event
        event = Event(
            id=event_id,
            type="death",
            year=self.current_year,
            date_day=date_day,
            date_month=date_month,
            house_number=house_number,
            original_text=line,
            source_line=line_num,
            deceased=deceased_id,
            age_at_death=deceased_age,
            witnesses=witness_ids
        )

        self.events[event_id] = event

    def parse_marriage_line(self, line: str, line_num: int):
        """Parse marriage record"""
        event_id = self.get_next_event_id()

        # Extract witnesses
        witnesses = []
        witness_match = re.match(r'^[Śś]w[:.]\s*([^,]+),', line)
        if witness_match:
            witness_text = witness_match.group(1).strip()
            witnesses = self.parse_person_list(witness_text)

        # Extract couple
        couple_match = re.search(r',\s+([A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+\s+[A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+)\s+i\s+([A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+\s+[A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+)', line)

        groom_id = None
        bride_id = None

        if couple_match:
            groom_name = couple_match.group(1).strip().split()
            bride_name = couple_match.group(2).strip().split()

            if len(groom_name) >= 2:
                groom_id = self.find_or_create_person(groom_name[0], groom_name[1], gender="M", year_context=self.current_year)
            if len(bride_name) >= 2:
                bride_id = self.find_or_create_person(bride_name[0], bride_name[1], gender="F", year_context=self.current_year)

        witness_ids = [self.create_person_from_mention(w) for w in witnesses]

        event = Event(
            id=event_id,
            type="marriage",
            year=self.current_year,
            original_text=line,
            source_line=line_num,
            groom=groom_id,
            bride=bride_id,
            witnesses=witness_ids
        )

        self.events[event_id] = event

        if groom_id and bride_id:
            self.add_relationship("marriage", groom_id, bride_id, None, [event_id])

    def parse_person_list(self, text: str) -> List[Dict]:
        """Parse a list of people (witnesses)"""
        people = []

        # Split by 'i' (and)
        parts = re.split(r'\s+[iI]\s+', text)

        for part in parts:
            part = part.strip()
            if not part or part in ['X', 'NN', '?']:
                continue

            # Extract name and age: "Name Surname (age, info)"
            match = re.match(r'([A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+)(?:\s+([A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+))?(?:\s+\((\d+)[^\)]*\))?', part)

            if match:
                given_name = match.group(1)
                surname = match.group(2) if match.group(2) else None
                age = int(match.group(3)) if match.group(3) else None

                people.append({
                    'given_name': given_name,
                    'surname': surname,
                    'age': age,
                    'full_text': part
                })

        return people

    def parse_person_list_with_initials(self, text: str) -> List[Dict]:
        """Parse godparents list, resolving initials"""
        people = []

        # Split by 'i' (and)
        parts = re.split(r'\s+[iI]\s+', text)

        for part in parts:
            part = part.strip()
            if not part or part in ['X', 'NN', '?']:
                continue

            # Check if it's initials (e.g., "K.Ł." or "O.Z.")
            initial_match = re.match(r'^([A-ZŹŻĄĘĆŁŃÓŚ])\.([A-ZŹŻĄĘĆŁŃÓŚ])\.?$', part)
            if initial_match:
                # Try to resolve from line_person_map
                for key, person_id in self.line_person_map.items():
                    if key.startswith(f"{initial_match.group(1)}.{initial_match.group(2)}."):
                        people.append({'resolved_id': person_id})
                        break
                continue

            # Regular name
            match = re.match(r'([A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+)(?:\s+([A-ZŹŻĄĘĆŁŃÓŚ][a-zźżąęćłńóś]+))?', part)
            if match:
                given_name = match.group(1)
                surname = match.group(2) if match.group(2) else None

                people.append({
                    'given_name': given_name,
                    'surname': surname
                })

        return people

    def create_person_from_mention(self, mention: Dict) -> Optional[str]:
        """Create or find person from a mention dict"""
        if not mention:
            return None

        # Check if already resolved
        if 'resolved_id' in mention:
            return mention['resolved_id']

        given_name = mention.get('given_name')
        surname = mention.get('surname')
        age = mention.get('age')

        if not given_name:
            return None

        birth_year = self.current_year - age if age else None

        return self.find_or_create_person(
            given_name,
            surname or "Unknown",
            birth_year=birth_year,
            year_context=self.current_year
        )

    def infer_gender_from_polish_name(self, given_name: str) -> tuple[str, str, str]:
        """
        Infer gender from Polish first name rules.
        Returns: (gender, confidence, reason)
        - gender: 'M', 'F', or 'U'
        - confidence: 'high', 'medium', 'low'
        - reason: explanation for classification
        """
        original_name = given_name

        # Handle compound first names (e.g., "Jan Kapistran")
        # Use first name for primary classification
        name_parts = given_name.split()
        if len(name_parts) > 1:
            primary_name = name_parts[0]
            compound_note = f" (compound name: {given_name})"
        else:
            primary_name = given_name
            compound_note = ""

        # Known male names (for high confidence)
        known_male_names = {
            'Jan', 'Józef', 'Wojciech', 'Kazimierz', 'Wawrzyniec', 'Stanisław',
            'Piotr', 'Antoni', 'Franciszek', 'Marcin', 'Jakub', 'Tomasz',
            'Ignacy', 'Leonard', 'Fabian', 'Mateusz', 'Adam', 'Onufry',
            'Wincenty', 'Krzysztof', 'Szczepan', 'Jędrzej', 'Dominik',
            'Grzegorz', 'Łukasz', 'Melchior', 'Tadeusz', 'Stefan', 'Mikołaj',
            'Andrzej', 'Paweł', 'Bartłomiej', 'Filip', 'Maciej', 'Szymon',
            'Błażej', 'Sebastian', 'Michał', 'Gabriel', 'Kuba', 'Kosma',
            'Barnaba', 'Bonawentura', 'Kapistran'
        }

        # Known female names (for high confidence)
        known_female_names = {
            'Marianna', 'Brygida', 'Helena', 'Agnieszka', 'Rozalia',
            'Franciszka', 'Katarzyna', 'Elżbieta', 'Magdalena', 'Anastazja',
            'Tekla', 'Salomea', 'Antonina', 'Martyna', 'Teresa', 'Zofia',
            'Anna', 'Barbara', 'Ewa', 'Jadwiga', 'Krystyna', 'Małgorzata',
            'Dorota', 'Urszula', 'Joanna', 'Monika', 'Weronika'
        }

        # Check known names first (high confidence)
        if primary_name in known_male_names:
            return ('M', 'high', f'Known Polish male name: {primary_name}{compound_note}')

        if primary_name in known_female_names:
            return ('F', 'high', f'Known Polish female name: {primary_name}{compound_note}')

        # Apply ending rules
        # Polish female names typically end with 'a', 'ia', 'ja'
        if primary_name.endswith(('a', 'ia', 'ja')):
            # Check if it's a male exception
            male_exceptions = ['Kuba', 'Kosma', 'Barnaba', 'Bonawentura', 'Kapistran']
            if primary_name in male_exceptions:
                return ('M', 'high', f'Male exception ending in "a": {primary_name}{compound_note}')
            return ('F', 'medium', f'Polish name ending in "a": {primary_name}{compound_note}')

        # Names ending in consonants are typically male
        if primary_name[-1] in 'bcdfghjklmnprstwzćłńśźż':
            return ('M', 'medium', f'Polish name ending in consonant: {primary_name}{compound_note}')

        # Names ending in other vowels (e, i, o, u, y)
        if primary_name[-1] in 'eiouy':
            # Less certain, but more likely male in Polish
            return ('M', 'low', f'Name ending in vowel "{primary_name[-1]}": {primary_name}{compound_note}')

        # Unknown - couldn't classify
        return ('U', 'low', f'Unable to classify: {primary_name}{compound_note}')

    def find_or_create_person(self, given_name: str, surname: str,
                              gender: str = "U",
                              maiden_name: Optional[str] = None,
                              birth_year: Optional[int] = None,
                              death_year: Optional[int] = None,
                              year_context: Optional[int] = None) -> str:
        """Find existing or create new person"""

        # Check for user corrections first
        correction_key = f"{given_name}|{surname}"
        if correction_key in self.gender_corrections:
            gender = self.gender_corrections[correction_key]
            gender_confidence = 'high'
            gender_reason = 'user corrected'
        elif gender == "U":
            # Infer gender if not specified
            gender, gender_confidence, gender_reason = self.infer_gender_from_polish_name(given_name)

            # Track uncertain classifications (low or medium confidence)
            if gender_confidence in ['low', 'medium']:
                self.gender_uncertainties.append({
                    'given_name': given_name,
                    'surname': surname,
                    'inferred_gender': gender,
                    'confidence': gender_confidence,
                    'reason': gender_reason,
                    'birth_year': birth_year,
                    'year_context': year_context,
                    'maiden_name': maiden_name
                })
        else:
            gender_confidence = 'high'
            gender_reason = 'explicitly provided'

        full_name = f"{given_name} {surname}".lower()

        # Look for existing person with same name
        for pid, person in self.persons.items():
            if person.given_name.lower() == given_name.lower() and person.surname.lower() == surname.lower():
                # Check if birth years are compatible
                if birth_year and person.birth_year_estimate:
                    if abs(birth_year - person.birth_year_estimate) <= 5:
                        # Update with new info
                        if maiden_name and not person.maiden_name:
                            person.maiden_name = maiden_name
                        if death_year and not person.death_year_estimate:
                            person.death_year_estimate = death_year
                        if gender != "U" and person.gender == "U":
                            person.gender = gender
                        return pid
                elif not birth_year or not person.birth_year_estimate:
                    # No birth year info, assume same person
                    if maiden_name and not person.maiden_name:
                        person.maiden_name = maiden_name
                    if death_year and not person.death_year_estimate:
                        person.death_year_estimate = death_year
                    if gender != "U" and person.gender == "U":
                        person.gender = gender
                    return pid

        # Create new person
        person_id = self.get_next_person_id()
        person = Person(
            id=person_id,
            given_name=given_name,
            surname=surname,
            maiden_name=maiden_name,
            gender=gender,
            birth_year_estimate=birth_year,
            death_year_estimate=death_year
        )

        self.persons[person_id] = person
        return person_id

    def add_relationship(self, rel_type: str, from_id: str, to_id: str,
                        role: Optional[str], evidence: List[str]):
        if not from_id or not to_id:
            return

        # Check if relationship already exists
        for rel in self.relationships.values():
            # For marriage (symmetric), check both directions
            if rel_type == "marriage":
                if ((rel.type == rel_type and rel.from_person == from_id and rel.to_person == to_id) or
                    (rel.type == rel_type and rel.from_person == to_id and rel.to_person == from_id)):
                    rel.evidence.extend(evidence)
                    return
            else:
                # For other relationships, check exact match
                if (rel.type == rel_type and rel.from_person == from_id and
                    rel.to_person == to_id and rel.role == role):
                    rel.evidence.extend(evidence)
                    return

        rel_id = self.get_next_relationship_id()
        relationship = Relationship(
            id=rel_id,
            type=rel_type,
            from_person=from_id,
            to_person=to_id,
            role=role,
            evidence=evidence
        )

        self.relationships[rel_id] = relationship

    def get_next_person_id(self) -> str:
        self.person_counter += 1
        return f"P{self.person_counter:04d}"

    def get_next_event_id(self) -> str:
        self.event_counter += 1
        return f"E{self.event_counter:04d}"

    def get_next_relationship_id(self) -> str:
        self.relationship_counter += 1
        return f"R{self.relationship_counter:04d}"

    def export_to_json(self, output_dir: str):
        import os
        os.makedirs(output_dir, exist_ok=True)

        persons_dict = {pid: p.to_dict() for pid, p in self.persons.items()}
        events_dict = {eid: e.to_dict() for eid, e in self.events.items()}
        relationships_dict = {rid: r.to_dict() for rid, r in self.relationships.items()}

        with open(os.path.join(output_dir, 'persons.json'), 'w', encoding='utf-8') as f:
            json.dump(persons_dict, f, ensure_ascii=False, indent=2)

        with open(os.path.join(output_dir, 'events.json'), 'w', encoding='utf-8') as f:
            json.dump(events_dict, f, ensure_ascii=False, indent=2)

        with open(os.path.join(output_dir, 'relationships.json'), 'w', encoding='utf-8') as f:
            json.dump(relationships_dict, f, ensure_ascii=False, indent=2)

        combined = {
            "persons": persons_dict,
            "events": events_dict,
            "relationships": relationships_dict,
            "metadata": {
                "total_persons": len(persons_dict),
                "total_events": len(events_dict),
                "total_relationships": len(relationships_dict)
            }
        }

        with open(os.path.join(output_dir, 'genealogy_complete.json'), 'w', encoding='utf-8') as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)

        # Export gender uncertainties for review
        if self.gender_uncertainties:
            uncertainty_file = {
                "instructions": "Please review the gender classifications below. If you disagree with any classification, add a 'corrected_gender' field with value 'M' or 'F'. Save the file and rerun the parser.",
                "total_uncertain": len(self.gender_uncertainties),
                "classifications": self.gender_uncertainties
            }
            with open(os.path.join(output_dir, 'gender_review.json'), 'w', encoding='utf-8') as f:
                json.dump(uncertainty_file, f, ensure_ascii=False, indent=2)
            print(f"⚠ {len(self.gender_uncertainties)} uncertain gender classifications saved to gender_review.json")

        print(f"✓ Exported {len(persons_dict)} persons")
        print(f"✓ Exported {len(events_dict)} events")
        print(f"✓ Exported {len(relationships_dict)} relationships")

        # Gender statistics
        gender_counts = {'M': 0, 'F': 0, 'U': 0}
        for person in self.persons.values():
            gender_counts[person.gender] = gender_counts.get(person.gender, 0) + 1
        print(f"📊 Gender distribution: {gender_counts['M']} Male, {gender_counts['F']} Female, {gender_counts['U']} Unknown")


def main():
    print("=" * 70)
    print("Genealogical Data Parser V2 - Corrected Format")
    print("=" * 70)
    print()

    input_file = "/Users/kulikj01/Desktop/git/mein/mal/base.md"
    output_dir = "/Users/kulikj01/Desktop/git/mein/mal/data"
    corrections_file = "/Users/kulikj01/Desktop/git/mein/mal/data/gender_review.json"
    merge_log_file = "/Users/kulikj01/Desktop/git/mein/mal/data/merge_log.json"

    parser = GenealogyParserV2(
        corrections_file=corrections_file,
        merge_log_file=merge_log_file
    )

    print(f"Reading: {input_file}")
    parser.parse_file(input_file)

    print()
    print("Exporting to JSON...")
    parser.export_to_json(output_dir)

    print()
    print("=" * 70)
    print("Processing complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
