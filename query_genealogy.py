#!/usr/bin/env python3
"""
Genealogical Query Tool
Query relationships and connections in the structured genealogical database
"""

import json
from collections import deque
from typing import List, Dict, Optional, Set, Tuple


class GenealogyQuery:
    """Query tool for genealogical data"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.persons = {}
        self.events = {}
        self.relationships = {}
        self.load_data()

    def load_data(self):
        """Load all JSON data"""
        with open(f"{self.data_dir}/persons.json", 'r', encoding='utf-8') as f:
            self.persons = json.load(f)

        with open(f"{self.data_dir}/events.json", 'r', encoding='utf-8') as f:
            self.events = json.load(f)

        with open(f"{self.data_dir}/relationships.json", 'r', encoding='utf-8') as f:
            self.relationships = json.load(f)

        print(f"Loaded {len(self.persons)} persons, {len(self.events)} events, {len(self.relationships)} relationships")

    def find_person_by_name(self, name: str) -> List[Dict]:
        """Find person by name (fuzzy match)"""
        name_lower = name.lower()
        matches = []

        for pid, person in self.persons.items():
            person_name = f"{person['given_name']} {person['surname']}".lower()
            if name_lower in person_name or person_name in name_lower:
                matches.append({**person, 'id': pid})

        return matches

    def get_person(self, person_id: str) -> Optional[Dict]:
        """Get person by ID"""
        return self.persons.get(person_id)

    def get_parents(self, person_id: str) -> Dict[str, Optional[str]]:
        """Get parents of a person"""
        parents = {"father": None, "mother": None}

        for rel in self.relationships.values():
            if rel["type"] == "biological_parent" and rel["to_person"] == person_id:
                if rel.get("role") == "father":
                    parents["father"] = rel["from_person"]
                elif rel.get("role") == "mother":
                    parents["mother"] = rel["from_person"]

        return parents

    def get_children(self, person_id: str) -> List[str]:
        """Get children of a person"""
        children = []

        for rel in self.relationships.values():
            if rel["type"] == "biological_parent" and rel["from_person"] == person_id:
                children.append(rel["to_person"])

        return list(set(children))

    def get_siblings(self, person_id: str) -> List[str]:
        """Get siblings of a person"""
        parents = self.get_parents(person_id)
        siblings = set()

        # Find all children of the same parents
        for parent_id in [parents["father"], parents["mother"]]:
            if parent_id:
                children = self.get_children(parent_id)
                siblings.update(children)

        # Remove self
        siblings.discard(person_id)

        return list(siblings)

    def get_spouse(self, person_id: str) -> List[str]:
        """Get spouse(s) of a person"""
        spouses = []

        for rel in self.relationships.values():
            if rel["type"] == "marriage":
                if rel["from_person"] == person_id:
                    spouses.append(rel["to_person"])
                elif rel["to_person"] == person_id:
                    spouses.append(rel["from_person"])

        return spouses

    def get_birth_event(self, person_id: str) -> Optional[Dict]:
        """Get birth event for a person"""
        for event in self.events.values():
            if event["type"] == "birth" and event.get("child") == person_id:
                return event
        return None

    def get_death_event(self, person_id: str) -> Optional[Dict]:
        """Get death event for a person"""
        for event in self.events.values():
            if event["type"] == "death" and event.get("deceased") == person_id:
                return event
        return None

    def get_all_events_for_person(self, person_id: str) -> List[Dict]:
        """Get all events mentioning a person"""
        events = []

        for event in self.events.values():
            # Check if person is involved in any capacity
            if (event.get("child") == person_id or
                event.get("father") == person_id or
                event.get("mother") == person_id or
                event.get("deceased") == person_id or
                event.get("groom") == person_id or
                event.get("bride") == person_id or
                person_id in event.get("witnesses", []) or
                person_id in event.get("godparents", [])):
                events.append(event)

        # Sort by year
        events.sort(key=lambda e: e["date"].get("year", 0))
        return events

    def find_relationship_path(self, person_a: str, person_b: str) -> Optional[List[Tuple[str, str]]]:
        """Find relationship path between two people using BFS"""
        if person_a == person_b:
            return []

        # Build adjacency graph
        graph = {}
        for pid in self.persons.keys():
            graph[pid] = set()

        # Add parent-child relationships (bidirectional)
        for rel in self.relationships.values():
            if rel["type"] == "biological_parent":
                graph[rel["from_person"]].add((rel["to_person"], "child"))
                graph[rel["to_person"]].add((rel["from_person"], "parent"))
            elif rel["type"] == "marriage":
                graph[rel["from_person"]].add((rel["to_person"], "spouse"))
                graph[rel["to_person"]].add((rel["from_person"], "spouse"))

        # BFS
        queue = deque([(person_a, [])])
        visited = {person_a}

        while queue:
            current, path = queue.popleft()

            for neighbor, rel_type in graph.get(current, []):
                if neighbor == person_b:
                    return path + [(current, rel_type)]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [(current, rel_type)]))

        return None

    def describe_relationship(self, person_a: str, person_b: str) -> str:
        """Describe relationship between two people"""
        path = self.find_relationship_path(person_a, person_b)

        if path is None:
            return "No relationship found"

        if len(path) == 0:
            return "Same person"

        # Interpret path
        rel_description = []
        for pid, rel_type in path:
            person = self.persons[pid]
            name = f"{person['given_name']} {person['surname']}"
            rel_description.append(f"{name} ({rel_type})")

        return " → ".join(rel_description)

    def print_person_summary(self, person_id: str):
        """Print detailed summary of a person"""
        person = self.persons.get(person_id)
        if not person:
            print(f"Person {person_id} not found")
            return

        print("=" * 70)
        print(f"Person: {person['given_name']} {person['surname']}")
        print("=" * 70)

        if person.get("maiden_name"):
            print(f"Maiden name: {person['maiden_name']}")

        print(f"Gender: {person.get('gender', 'Unknown')}")

        if person.get("birth_year_estimate"):
            print(f"Birth year (estimate): {person['birth_year_estimate']}")

        if person.get("death_year_estimate"):
            print(f"Death year (estimate): {person['death_year_estimate']}")

        if person.get("occupations"):
            print(f"Occupations: {', '.join(person['occupations'])}")

        # Parents
        print("\nFamily:")
        parents = self.get_parents(person_id)
        if parents["father"]:
            father = self.persons[parents["father"]]
            print(f"  Father: {father['given_name']} {father['surname']} ({parents['father']})")
        if parents["mother"]:
            mother = self.persons[parents["mother"]]
            maiden = f" (z d. {mother.get('maiden_name')})" if mother.get('maiden_name') else ""
            print(f"  Mother: {mother['given_name']} {mother['surname']}{maiden} ({parents['mother']})")

        # Spouse(s)
        spouses = self.get_spouse(person_id)
        if spouses:
            print("\nSpouse(s):")
            for spouse_id in spouses:
                spouse = self.persons[spouse_id]
                print(f"  {spouse['given_name']} {spouse['surname']} ({spouse_id})")

        # Children
        children = self.get_children(person_id)
        if children:
            print(f"\nChildren ({len(children)}):")
            for child_id in children:
                child = self.persons[child_id]
                birth_year = child.get('birth_year_estimate', '?')
                print(f"  {child['given_name']} {child['surname']} (b. {birth_year}) ({child_id})")

        # Siblings
        siblings = self.get_siblings(person_id)
        if siblings:
            print(f"\nSiblings ({len(siblings)}):")
            for sibling_id in siblings:
                sibling = self.persons[sibling_id]
                print(f"  {sibling['given_name']} {sibling['surname']} ({sibling_id})")

        # Events
        print("\nEvents:")
        events = self.get_all_events_for_person(person_id)
        for event in events[:10]:  # Limit to 10
            year = event["date"].get("year", "?")
            event_type = event["type"]
            print(f"  {year}: {event_type.upper()} - {event['original_text'][:80]}...")

        print()

    def search_by_surname(self, surname: str) -> List[Dict]:
        """Find all persons with a given surname"""
        matches = []
        surname_lower = surname.lower()

        for pid, person in self.persons.items():
            if person['surname'].lower() == surname_lower:
                matches.append({**person, 'id': pid})

        return matches


def main():
    import sys

    data_dir = "/Users/kulikj01/Desktop/git/mein/mal/data"

    print("=" * 70)
    print("Genealogical Query Tool")
    print("=" * 70)
    print()

    query = GenealogyQuery(data_dir)
    print()

    # Example queries
    print("EXAMPLE QUERIES:")
    print("=" * 70)
    print()

    # Find Brygida Słyk (née Surdey)
    print("1. Searching for 'Brygida Słyk'...")
    matches = query.find_person_by_name("Brygida Słyk")
    if matches:
        for match in matches[:3]:
            print(f"   Found: {match['given_name']} {match['surname']} ({match['id']}) - born ~{match.get('birth_year_estimate', '?')}")
            brygida_id = match['id']

        print()
        print("   Detailed information:")
        query.print_person_summary(brygida_id)

    # Find all Surdey family members
    print("\n2. All members of the Surdey family:")
    surdeys = query.search_by_surname("Surdey")
    print(f"   Found {len(surdeys)} persons with surname Surdey")
    for person in surdeys[:10]:
        birth = person.get('birth_year_estimate', '?')
        death = person.get('death_year_estimate', '?')
        print(f"   - {person['given_name']} ({person['id']}) b.{birth} d.{death}")

    # Find relationship
    print("\n3. Finding relationship between two people...")
    if len(surdeys) >= 2:
        person_a = surdeys[0]['id']
        person_b = surdeys[1]['id']
        print(f"   Between {surdeys[0]['given_name']} ({person_a}) and {surdeys[1]['given_name']} ({person_b})")
        relationship = query.describe_relationship(person_a, person_b)
        print(f"   Relationship: {relationship}")

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
