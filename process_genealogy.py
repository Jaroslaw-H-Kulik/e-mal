#!/usr/bin/env python3
"""
Genealogical Data Structuring Tool
Transforms Polish genealogical records (1826-1914) into structured JSON format
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Set
from datetime import date
from collections import defaultdict

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Person:
    """Represents a unique individual in the genealogical database"""
    id: str
    given_name: str
    surname: str
    maiden_name: Optional[str] = None
    gender: str = "U"  # M/F/U (unknown)
    birth_year_estimate: Optional[int] = None
    death_year_estimate: Optional[int] = None
    confidence: str = "unknown"  # high/medium/low/unknown
    disambiguation_notes: str = ""
    occupations: List[str] = field(default_factory=list)
    alternate_names: List[str] = field(default_factory=list)

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None and v != [] and v != ""}


@dataclass
class DateInfo:
    """Represents a date with uncertainty information"""
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    display: str = ""
    certainty: str = "exact"  # exact/estimated/uncertain

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None and v != ""}


@dataclass
class Location:
    """Represents a location"""
    house_number: Optional[str] = None
    village: Optional[str] = None
    parish: str = "Grzybowa Góra"

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Event:
    """Base class for genealogical events"""
    id: str
    type: str  # birth/death/marriage
    date: DateInfo
    location: Location
    source_line: int
    original_text: str
    witnesses: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self):
        result = {
            "id": self.id,
            "type": self.type,
            "date": self.date.to_dict(),
            "location": self.location.to_dict(),
            "source_line": self.source_line,
            "original_text": self.original_text,
        }
        if self.witnesses:
            result["witnesses"] = self.witnesses
        if self.notes:
            result["notes"] = self.notes
        return result


@dataclass
class BirthEvent(Event):
    """Birth event with child, parents, and godparents"""
    child: Optional[str] = None
    father: Optional[str] = None
    mother: Optional[str] = None
    godparents: List[str] = field(default_factory=list)

    def to_dict(self):
        result = super().to_dict()
        if self.child:
            result["child"] = self.child
        if self.father:
            result["father"] = self.father
        if self.mother:
            result["mother"] = self.mother
        if self.godparents:
            result["godparents"] = self.godparents
        return result


@dataclass
class DeathEvent(Event):
    """Death event with deceased person and age"""
    deceased: Optional[str] = None
    age_at_death: Optional[int] = None

    def to_dict(self):
        result = super().to_dict()
        if self.deceased:
            result["deceased"] = self.deceased
        if self.age_at_death is not None:
            result["age_at_death"] = self.age_at_death
        return result


@dataclass
class MarriageEvent(Event):
    """Marriage event with groom and bride"""
    groom: Optional[str] = None
    bride: Optional[str] = None

    def to_dict(self):
        result = super().to_dict()
        if self.groom:
            result["groom"] = self.groom
        if self.bride:
            result["bride"] = self.bride
        return result


@dataclass
class Relationship:
    """Explicit relationship between two persons"""
    id: str
    type: str  # biological_parent/marriage/sibling/godparent/witness
    from_person: str
    to_person: str
    role: Optional[str] = None  # father/mother/godfather/godmother/etc
    evidence: List[str] = field(default_factory=list)  # event IDs
    confidence: str = "high"

    def to_dict(self):
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None and v != []}


# ============================================================================
# Parser
# ============================================================================

class GenealogyParser:
    """Main parser for genealogical records"""

    def __init__(self):
        self.persons: Dict[str, Person] = {}
        self.events: Dict[str, Event] = {}
        self.relationships: Dict[str, Relationship] = {}
        self.person_counter = 0
        self.event_counter = 0
        self.relationship_counter = 0

        # Temporary storage for person mentions (before disambiguation)
        self.person_mentions: List[Dict] = []
        self.name_to_person_ids: Dict[str, List[str]] = defaultdict(list)

        self.current_year = None
        self.current_section = None  # narodziny/zejścia/śluby

    def parse_file(self, filepath: str):
        """Parse the genealogical data file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue

            # Extract line number if present (format: "123→content")
            match = re.match(r'(\d+)→(.+)', line)
            if match:
                original_line_num = int(match.group(1))
                content = match.group(2).strip()
            else:
                original_line_num = line_num
                content = line

            # Check for year marker
            year_match = re.match(r'^(\d{4}):?\s*$', content)
            if year_match:
                self.current_year = int(year_match.group(1))
                self.current_section = None
                continue

            # Check for section marker
            if content in ['narodziny:', 'zejścia:', 'śluby:', 'urodzenia:']:
                self.current_section = content.rstrip(':')
                continue

            # Parse event line
            if self.current_year:
                self.parse_event_line(content, original_line_num)

    def parse_event_line(self, line: str, line_num: int):
        """Parse a single event line"""
        # Determine event type from section or content
        if self.current_section in ['narodziny', 'urodzenia']:
            self.parse_birth_line(line, line_num)
        elif self.current_section == 'zejścia':
            self.parse_death_line(line, line_num)
        elif self.current_section == 'śluby':
            self.parse_marriage_line(line, line_num)
        else:
            # Try to infer from content
            if 'św:' in line and 'ur:' in line.lower():
                self.parse_birth_line(line, line_num)
            elif 'św:' in line and 'zm:' in line.lower():
                self.parse_death_line(line, line_num)

    def parse_birth_line(self, line: str, line_num: int):
        """Parse a birth record"""
        event_id = self.get_next_event_id()

        # Extract main components
        # Format: Father and Mother z d. MaidenName, św: witnesses - chrz. godparents. Ur: child

        # Parse father and mother
        parents_match = re.match(r'^([^,]+?)\s+i\s+([^,]+?)\s+z\s+d\.?\s+([^:,]+)', line)
        if not parents_match:
            # Try simpler pattern
            parents_match = re.match(r'^([^,]+?)\s+i\s+([^:,]+)', line)

        father_name = None
        mother_name = None
        mother_maiden = None

        if parents_match:
            father_text = parents_match.group(1).strip()
            if len(parents_match.groups()) >= 3:
                mother_text = parents_match.group(2).strip()
                mother_maiden_raw = parents_match.group(3).strip()
                # Clean maiden name - remove ages and extra info
                mother_maiden = re.sub(r'\s*\([^\)]+\)', '', mother_maiden_raw).strip()
            else:
                mother_text = parents_match.group(2).strip()

            # Extract father details
            father_name = self.extract_name_and_age(father_text)
            # Extract mother details
            mother_name = self.extract_name_and_age(mother_text)

        # Extract witnesses (św:)
        witnesses = []
        witness_match = re.search(r'św:\s*([^-]+?)(?:\s+-\s+chrz|chrz)', line, re.IGNORECASE)
        if witness_match:
            witness_text = witness_match.group(1).strip()
            witnesses = self.parse_person_list(witness_text)

        # Extract godparents (chrz.)
        godparents = []
        godparent_match = re.search(r'chrz\.?\s*([^.]+?)(?:\.\s*[Uu]r[:.]|$)', line, re.IGNORECASE)
        if godparent_match:
            godparent_text = godparent_match.group(1).strip()
            godparents = self.parse_person_list(godparent_text)

        # Extract child (Ur: or ur:)
        child_name = None
        child_match = re.search(r'[Uu]r[:.\s]+([^,\(\)]+?)(?:\s*[-\(]|$)', line)
        if child_match:
            child_name = child_match.group(1).strip()

        # Extract house number
        house_num = None
        house_match = re.search(r'dom\s+(\d+[a-z]?|\?|X)', line, re.IGNORECASE)
        if house_match:
            house_num = house_match.group(1)

        # Extract specific date if present
        date_match = re.search(r'\((\d{1,2})\.(\d{1,2})\)', line)
        date_info = DateInfo(year=self.current_year)
        if date_match:
            date_info.day = int(date_match.group(1))
            date_info.month = int(date_match.group(2))

        location = Location(house_number=house_num)

        # Create or find person IDs
        father_id = self.find_or_create_person(father_name, self.current_year, "father") if father_name else None
        mother_id = self.find_or_create_person(mother_name, self.current_year, "mother", maiden_name=mother_maiden) if mother_name else None
        child_id = self.find_or_create_person(child_name, self.current_year, "child", birth_year=self.current_year) if child_name else None

        witness_ids = [self.find_or_create_person(w, self.current_year, "witness") for w in witnesses]
        godparent_ids = [self.find_or_create_person(g, self.current_year, "godparent") for g in godparents]

        # Create birth event
        birth_event = BirthEvent(
            id=event_id,
            type="birth",
            date=date_info,
            location=location,
            source_line=line_num,
            original_text=line,
            child=child_id,
            father=father_id,
            mother=mother_id,
            witnesses=witness_ids,
            godparents=godparent_ids
        )

        self.events[event_id] = birth_event

        # Create relationships
        if father_id and child_id:
            self.add_relationship("biological_parent", father_id, child_id, "father", [event_id])
        if mother_id and child_id:
            self.add_relationship("biological_parent", mother_id, child_id, "mother", [event_id])
        for gp_id in godparent_ids:
            if child_id:
                self.add_relationship("godparent", gp_id, child_id, "godparent", [event_id])

    def parse_death_line(self, line: str, line_num: int):
        """Parse a death record"""
        event_id = self.get_next_event_id()

        # Format: św: witnesses, deceased_name (age, details), dom X (date)

        # Extract witnesses
        witnesses = []
        witness_match = re.match(r'^[Śś]w[:.]\s*([^,]+)', line)
        if witness_match:
            witness_text = witness_match.group(1).strip()
            witnesses = self.parse_person_list(witness_text)

        # Extract deceased and age
        # Pattern: Name (age, details) or Name (details)
        deceased_match = re.search(r',\s*([^,\(]+?)(?:\s*\(([^\)]+)\))?(?:,\s*dom\s+|$)', line)

        deceased_name = None
        age = None

        if deceased_match:
            deceased_name = deceased_match.group(1).strip()
            if deceased_match.group(2):
                age_text = deceased_match.group(2)
                age_num = re.search(r'(\d+)\s*(?:lat|rok|miesię|tygodn|dni)', age_text, re.IGNORECASE)
                if age_num:
                    age = int(age_num.group(1))

        # Extract house number
        house_num = None
        house_match = re.search(r'dom\s+(\d+[a-z]?|\?|X)', line, re.IGNORECASE)
        if house_match:
            house_num = house_match.group(1)

        # Extract date
        date_match = re.search(r'\((\d{1,2})\.(\d{1,2})\)', line)
        date_info = DateInfo(year=self.current_year)
        if date_match:
            date_info.day = int(date_match.group(1))
            date_info.month = int(date_match.group(2))

        location = Location(house_number=house_num)

        # Create person IDs
        deceased_id = self.find_or_create_person(deceased_name, self.current_year, "deceased", death_year=self.current_year, age_at_death=age) if deceased_name else None
        witness_ids = [self.find_or_create_person(w, self.current_year, "witness") for w in witnesses]

        # Create death event
        death_event = DeathEvent(
            id=event_id,
            type="death",
            date=date_info,
            location=location,
            source_line=line_num,
            original_text=line,
            deceased=deceased_id,
            age_at_death=age,
            witnesses=witness_ids
        )

        self.events[event_id] = death_event

    def parse_marriage_line(self, line: str, line_num: int):
        """Parse a marriage record"""
        event_id = self.get_next_event_id()

        # Format: św: witnesses, Groom and Bride

        # Extract witnesses
        witnesses = []
        witness_match = re.match(r'^[Śś]w[:.]\s*([^,]+)', line)
        if witness_match:
            witness_text = witness_match.group(1).strip()
            witnesses = self.parse_person_list(witness_text)

        # Extract groom and bride
        couple_match = re.search(r',\s*([^,]+?)\s+i\s+([^,\(]+)', line)

        groom_name = None
        bride_name = None

        if couple_match:
            groom_name = couple_match.group(1).strip()
            bride_name = couple_match.group(2).strip()

        date_info = DateInfo(year=self.current_year)
        location = Location()

        # Create person IDs
        groom_id = self.find_or_create_person(groom_name, self.current_year, "groom") if groom_name else None
        bride_id = self.find_or_create_person(bride_name, self.current_year, "bride") if bride_name else None
        witness_ids = [self.find_or_create_person(w, self.current_year, "witness") for w in witnesses]

        # Create marriage event
        marriage_event = MarriageEvent(
            id=event_id,
            type="marriage",
            date=date_info,
            location=location,
            source_line=line_num,
            original_text=line,
            groom=groom_id,
            bride=bride_id,
            witnesses=witness_ids
        )

        self.events[event_id] = marriage_event

        # Create marriage relationship
        if groom_id and bride_id:
            self.add_relationship("marriage", groom_id, bride_id, None, [event_id])

    def extract_name_and_age(self, text: str) -> Dict:
        """Extract name, age, and occupation from text"""
        # Pattern: Name Surname (age, occupation)
        result = {"name": text}

        # Extract age
        age_match = re.search(r'\((\d+)[^\)]*\)', text)
        if age_match:
            result["age"] = int(age_match.group(1))
            # Remove age from name
            result["name"] = re.sub(r'\s*\([^\)]+\)', '', text).strip()

        # Extract occupation
        occupations = ['młynarz', 'wyrobnik', 'organista', 'kowal', 'podleśny', 'leśniczy',
                       'dziedzic', 'akuszerka', 'sztygar', 'górnik', 'karczmarz', 'cieśla']
        for occ in occupations:
            if occ in text.lower():
                result["occupation"] = occ
                break

        return result

    def parse_person_list(self, text: str) -> List[Dict]:
        """Parse a list of people (witnesses, godparents)"""
        # Split by 'i' (and) but preserve parentheses content
        people = []

        # Simple split for now
        parts = re.split(r'\s+i\s+', text)
        for part in parts:
            part = part.strip()
            if part and part not in ['X', 'NN', '?']:
                person_info = self.extract_name_and_age(part)
                people.append(person_info)

        return people

    def find_or_create_person(self, name_info: Dict, year: int, role: str,
                             maiden_name: Optional[str] = None,
                             birth_year: Optional[int] = None,
                             death_year: Optional[int] = None,
                             age_at_death: Optional[int] = None) -> str:
        """Find existing person or create new one"""

        if isinstance(name_info, str):
            name_info = {"name": name_info}

        name = name_info.get("name", "").strip()
        if not name or name in ['X', 'NN', '?']:
            return None

        # Clean up name - remove age in parentheses if still present
        name = re.sub(r'\s*\([^\)]+\)', '', name).strip()

        # Parse name into given name and surname
        name_parts = name.split()
        if len(name_parts) < 2:
            given_name = name_parts[0] if name_parts else "Unknown"
            surname = "Unknown"
        else:
            given_name = name_parts[0]
            surname = ' '.join(name_parts[1:])

        # Estimate birth year from age if available
        estimated_birth_year = None
        if "age" in name_info:
            estimated_birth_year = year - name_info["age"]
        elif birth_year:
            estimated_birth_year = birth_year
        elif death_year and age_at_death:
            estimated_birth_year = death_year - age_at_death

        # Check if person exists with improved matching
        full_name = f"{given_name} {surname}".lower()

        # Look for existing person with same name
        if full_name in self.name_to_person_ids:
            candidates = self.name_to_person_ids[full_name]

            # Try to find best match
            best_match = None
            for candidate_id in candidates:
                candidate = self.persons[candidate_id]

                # Check if birth years are compatible (within 5 years)
                if estimated_birth_year and candidate.birth_year_estimate:
                    year_diff = abs(estimated_birth_year - candidate.birth_year_estimate)
                    if year_diff <= 5:
                        best_match = candidate_id
                        break
                else:
                    # If no birth year info, use first match
                    best_match = candidate_id
                    break

            if best_match:
                # Update person with new information
                person = self.persons[best_match]
                if estimated_birth_year and not person.birth_year_estimate:
                    person.birth_year_estimate = estimated_birth_year
                if death_year and not person.death_year_estimate:
                    person.death_year_estimate = death_year
                if "occupation" in name_info and name_info["occupation"] not in person.occupations:
                    person.occupations.append(name_info["occupation"])
                if maiden_name and not person.maiden_name:
                    person.maiden_name = maiden_name
                return best_match

        # Create new person
        person_id = self.get_next_person_id()

        gender = "U"
        if role in ["father", "groom"]:
            gender = "M"
        elif role in ["mother", "bride"]:
            gender = "F"

        person = Person(
            id=person_id,
            given_name=given_name,
            surname=surname,
            maiden_name=maiden_name,
            gender=gender,
            birth_year_estimate=estimated_birth_year,
            death_year_estimate=death_year,
            occupations=[name_info["occupation"]] if "occupation" in name_info else []
        )

        self.persons[person_id] = person
        self.name_to_person_ids[full_name].append(person_id)

        return person_id

    def add_relationship(self, rel_type: str, from_id: str, to_id: str,
                        role: Optional[str], evidence: List[str]):
        """Add a relationship between two persons"""
        if not from_id or not to_id:
            return

        # Check if relationship already exists
        rel_key = f"{rel_type}_{from_id}_{to_id}_{role}"

        for rel in self.relationships.values():
            if (rel.type == rel_type and rel.from_person == from_id and
                rel.to_person == to_id and rel.role == role):
                # Add evidence to existing relationship
                rel.evidence.extend(evidence)
                return

        # Create new relationship
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
        """Export all data to JSON files"""
        import os

        os.makedirs(output_dir, exist_ok=True)

        # Convert to dictionaries
        persons_dict = {pid: p.to_dict() for pid, p in self.persons.items()}
        events_dict = {eid: e.to_dict() for eid, e in self.events.items()}
        relationships_dict = {rid: r.to_dict() for rid, r in self.relationships.items()}

        # Write separate files
        with open(os.path.join(output_dir, 'persons.json'), 'w', encoding='utf-8') as f:
            json.dump(persons_dict, f, ensure_ascii=False, indent=2)

        with open(os.path.join(output_dir, 'events.json'), 'w', encoding='utf-8') as f:
            json.dump(events_dict, f, ensure_ascii=False, indent=2)

        with open(os.path.join(output_dir, 'relationships.json'), 'w', encoding='utf-8') as f:
            json.dump(relationships_dict, f, ensure_ascii=False, indent=2)

        # Write combined file
        combined = {
            "persons": persons_dict,
            "events": events_dict,
            "relationships": relationships_dict,
            "metadata": {
                "total_persons": len(persons_dict),
                "total_events": len(events_dict),
                "total_relationships": len(relationships_dict),
                "year_range": [1826, 1914]
            }
        }

        with open(os.path.join(output_dir, 'genealogy_complete.json'), 'w', encoding='utf-8') as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)

        # Generate statistics
        stats = self.generate_statistics()
        with open(os.path.join(output_dir, 'statistics.json'), 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        # Generate disambiguation report
        disambiguation = self.generate_disambiguation_report()
        with open(os.path.join(output_dir, 'disambiguation_report.json'), 'w', encoding='utf-8') as f:
            json.dump(disambiguation, f, ensure_ascii=False, indent=2)

        print(f"✓ Exported {len(persons_dict)} persons")
        print(f"✓ Exported {len(events_dict)} events")
        print(f"✓ Exported {len(relationships_dict)} relationships")
        print(f"✓ Potential duplicates: {disambiguation['names_with_multiple_ids']}")
        print(f"✓ Files written to {output_dir}")

    def generate_statistics(self) -> Dict:
        """Generate summary statistics"""
        stats = {
            "total_persons": len(self.persons),
            "total_events": len(self.events),
            "total_relationships": len(self.relationships),
            "events_by_type": defaultdict(int),
            "relationships_by_type": defaultdict(int),
            "persons_by_gender": {"M": 0, "F": 0, "U": 0},
            "persons_with_birth_year": 0,
            "persons_with_death_year": 0,
            "persons_with_occupations": 0,
            "most_common_surnames": {},
        }

        for event in self.events.values():
            stats["events_by_type"][event.type] += 1

        for rel in self.relationships.values():
            stats["relationships_by_type"][rel.type] += 1

        surname_counts = defaultdict(int)
        for person in self.persons.values():
            stats["persons_by_gender"][person.gender] += 1
            if person.birth_year_estimate:
                stats["persons_with_birth_year"] += 1
            if person.death_year_estimate:
                stats["persons_with_death_year"] += 1
            if person.occupations:
                stats["persons_with_occupations"] += 1
            surname_counts[person.surname] += 1

        # Convert defaultdicts to regular dicts
        stats["events_by_type"] = dict(stats["events_by_type"])
        stats["relationships_by_type"] = dict(stats["relationships_by_type"])

        # Top 10 surnames
        sorted_surnames = sorted(surname_counts.items(), key=lambda x: x[1], reverse=True)
        stats["most_common_surnames"] = dict(sorted_surnames[:10])

        return stats

    def generate_disambiguation_report(self) -> Dict:
        """Generate report on potential duplicates requiring disambiguation"""
        report = {
            "duplicate_candidates": [],
            "total_unique_names": len(self.name_to_person_ids),
            "names_with_multiple_ids": 0
        }

        for full_name, person_ids in self.name_to_person_ids.items():
            if len(person_ids) > 1:
                report["names_with_multiple_ids"] += 1

                # Gather information about each candidate
                candidates = []
                for pid in person_ids:
                    person = self.persons[pid]
                    candidates.append({
                        "id": pid,
                        "given_name": person.given_name,
                        "surname": person.surname,
                        "birth_year": person.birth_year_estimate,
                        "death_year": person.death_year_estimate,
                        "gender": person.gender,
                        "occupations": person.occupations
                    })

                report["duplicate_candidates"].append({
                    "name": full_name,
                    "count": len(person_ids),
                    "candidates": candidates
                })

        # Sort by count
        report["duplicate_candidates"].sort(key=lambda x: x["count"], reverse=True)

        return report


# ============================================================================
# Main
# ============================================================================

def main():
    import sys

    input_file = "/Users/kulikj01/Desktop/git/mein/mal/base.md"
    output_dir = "/Users/kulikj01/Desktop/git/mein/mal/data"

    print("=" * 70)
    print("Genealogical Data Structuring Tool")
    print("=" * 70)
    print()

    parser = GenealogyParser()

    print(f"Reading input file: {input_file}")
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
