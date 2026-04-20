#!/usr/bin/env python3
"""
New Data Model for Genealogy Application
Implements the model described in events_feature_desc.txt Step 1
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import date
import json


@dataclass
class FlexibleDate:
    """
    Flexible date that can represent:
    - Just a year: FlexibleDate(year=1850)
    - Year and month: FlexibleDate(year=1850, month=3)
    - Full date: FlexibleDate(year=1850, month=3, day=15)
    - Approximate: FlexibleDate(year=1850, circa=True)
    """
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    circa: bool = False

    def to_dict(self):
        result = {}
        if self.year:
            result['year'] = self.year
        if self.month:
            result['month'] = self.month
        if self.day:
            result['day'] = self.day
        if self.circa:
            result['circa'] = True
        return result

    def display(self) -> str:
        """Return human-readable date string"""
        prefix = "circa " if self.circa else ""
        if self.day and self.month and self.year:
            return f"{prefix}{self.day:02d}/{self.month:02d}/{self.year}"
        elif self.month and self.year:
            return f"{prefix}{self.month:02d}/{self.year}"
        elif self.year:
            return f"{prefix}{self.year}"
        return "?"


@dataclass
class Person:
    """Person entity - represents an individual in the genealogy"""
    id: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    maiden_name: Optional[str] = None
    previous_last_names: List[str] = field(default_factory=list)
    gender: str = "U"  # M/F/U
    occupation: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        result = {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'gender': self.gender
        }

        if self.middle_name:
            result['middle_name'] = self.middle_name
        if self.maiden_name:
            result['maiden_name'] = self.maiden_name
        if self.previous_last_names:
            result['previous_last_names'] = self.previous_last_names
        if self.occupation:
            result['occupation'] = self.occupation
        if self.tags:
            result['tags'] = self.tags
        if self.links:
            result['links'] = self.links
        if self.notes:
            result['notes'] = self.notes

        return result


@dataclass
class Place:
    """Place entity - represents a location"""
    id: str
    name: str
    parish_name: Optional[str] = None
    house_number: Optional[str] = None

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        result = {
            'id': self.id,
            'name': self.name
        }

        if self.parish_name:
            result['parish_name'] = self.parish_name
        if self.house_number:
            result['house_number'] = self.house_number

        return result


@dataclass
class Event:
    """Event entity - represents a life event (birth, marriage, death, etc.)"""
    id: str
    type: str  # birth/baptism/marriage/death/burial
    date: Optional[FlexibleDate] = None
    place_id: Optional[str] = None
    content: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        result = {
            'id': self.id,
            'type': self.type
        }

        if self.date:
            result['date'] = self.date.to_dict()
        if self.place_id:
            result['place_id'] = self.place_id
        if self.content:
            result['content'] = self.content
        if self.tags:
            result['tags'] = self.tags
        if self.links:
            result['links'] = self.links
        if self.notes:
            result['notes'] = self.notes

        return result


@dataclass
class EventParticipation:
    """
    EventParticipation entity - links persons to events with roles
    Represents who participated in an event and in what capacity
    """
    id: str
    event_id: str
    person_id: str
    role: str  # child/father/mother/witness/godparent/spouse/deceased/etc.

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'person_id': self.person_id,
            'role': self.role
        }


@dataclass
class FamilyRelationship:
    """
    FamilyRelationship entity - represents family relationships between persons
    Can be derived from events or standalone
    """
    id: str
    person_1_id: str
    person_2_id: str
    type: str  # parent/child/spouse/sibling
    source_event_id: Optional[str] = None

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        result = {
            'id': self.id,
            'person_1_id': self.person_1_id,
            'person_2_id': self.person_2_id,
            'type': self.type
        }

        if self.source_event_id:
            result['source_event_id'] = self.source_event_id

        return result


@dataclass
class GenealogyDatabase:
    """Complete genealogy database"""
    persons: Dict[str, Person] = field(default_factory=dict)
    places: Dict[str, Place] = field(default_factory=dict)
    events: Dict[str, Event] = field(default_factory=dict)
    event_participations: Dict[str, EventParticipation] = field(default_factory=dict)
    family_relationships: Dict[str, FamilyRelationship] = field(default_factory=dict)

    def to_dict(self):
        """Convert entire database to dictionary for JSON serialization"""
        return {
            'persons': {pid: p.to_dict() for pid, p in self.persons.items()},
            'places': {pid: p.to_dict() for pid, p in self.places.items()},
            'events': {eid: e.to_dict() for eid, e in self.events.items()},
            'event_participations': {eid: ep.to_dict() for eid, ep in self.event_participations.items()},
            'family_relationships': {rid: fr.to_dict() for rid, fr in self.family_relationships.items()}
        }

    def save_to_file(self, filename: str):
        """Save database to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_file(cls, filename: str):
        """Load database from JSON file"""
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        db = cls()

        # Load persons
        for pid, pdata in data.get('persons', {}).items():
            db.persons[pid] = Person(
                id=pdata['id'],
                first_name=pdata['first_name'],
                last_name=pdata['last_name'],
                middle_name=pdata.get('middle_name'),
                maiden_name=pdata.get('maiden_name'),
                previous_last_names=pdata.get('previous_last_names', []),
                gender=pdata.get('gender', 'U'),
                occupation=pdata.get('occupation'),
                tags=pdata.get('tags', []),
                links=pdata.get('links', []),
                notes=pdata.get('notes')
            )

        # Load places
        for plid, pldata in data.get('places', {}).items():
            db.places[plid] = Place(**pldata)

        # Load events
        for eid, edata in data.get('events', {}).items():
            event_date = None
            if 'date' in edata:
                event_date = FlexibleDate(**edata['date'])

            db.events[eid] = Event(
                id=edata['id'],
                type=edata['type'],
                date=event_date,
                place_id=edata.get('place_id'),
                content=edata.get('content'),
                tags=edata.get('tags', []),
                links=edata.get('links', []),
                notes=edata.get('notes')
            )

        # Load event participations
        for epid, epdata in data.get('event_participations', {}).items():
            db.event_participations[epid] = EventParticipation(**epdata)

        # Load family relationships
        for frid, frdata in data.get('family_relationships', {}).items():
            db.family_relationships[frid] = FamilyRelationship(**frdata)

        return db


# Helper functions for ID generation
def get_next_id(existing_ids: List[str], prefix: str) -> str:
    """Generate next ID with given prefix"""
    if not existing_ids:
        return f"{prefix}0001"

    max_num = max([int(id[len(prefix):]) for id in existing_ids if id.startswith(prefix)], default=0)
    return f"{prefix}{(max_num + 1):04d}"
