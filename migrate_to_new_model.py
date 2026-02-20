#!/usr/bin/env python3
"""
Migration script to convert old genealogy data model to new event-centric model
"""

import json
import sys
from new_data_model import (
    GenealogyDatabase, Person, Place, Event, EventParticipation,
    FamilyRelationship, FlexibleDate, get_next_id
)


def migrate_old_to_new(old_data_path: str, new_data_path: str):
    """Migrate from old data model to new data model"""

    print("=" * 70)
    print("MIGRATION: Old Model → New Model")
    print("=" * 70)

    # Load old data
    print(f"\n📂 Loading old data from: {old_data_path}")
    with open(old_data_path, 'r', encoding='utf-8') as f:
        old_data = json.load(f)

    print(f"  ✓ Loaded {len(old_data.get('persons', {}))} persons")
    print(f"  ✓ Loaded {len(old_data.get('relationships', {}))} relationships")
    print(f"  ✓ Loaded {len(old_data.get('events', {}))} events")

    # Create new database
    new_db = GenealogyDatabase()

    # Step 1: Migrate Persons
    print("\n👤 Migrating persons...")
    migrate_persons(old_data.get('persons', {}), new_db)
    print(f"  ✓ Migrated {len(new_db.persons)} persons")

    # Step 2: Create Places (from events and person data)
    print("\n📍 Creating places...")
    create_places(old_data, new_db)
    print(f"  ✓ Created {len(new_db.places)} places")

    # Step 3: Migrate Events
    print("\n📅 Migrating events...")
    migrate_events(old_data.get('events', {}), new_db)
    print(f"  ✓ Migrated {len(new_db.events)} events")

    # Step 4: Create Event Participations (from old events)
    print("\n👥 Creating event participations...")
    create_event_participations(old_data.get('events', {}), new_db)
    print(f"  ✓ Created {len(new_db.event_participations)} event participations")

    # Step 5: Migrate Relationships to Family Relationships
    print("\n👨‍👩‍👧‍👦 Migrating family relationships...")
    migrate_relationships(old_data.get('relationships', {}), new_db)
    print(f"  ✓ Migrated {len(new_db.family_relationships)} family relationships")

    # Save new data
    print(f"\n💾 Saving new data to: {new_data_path}")
    new_db.save_to_file(new_data_path)
    print(f"  ✓ Saved successfully!")

    # Print summary
    print("\n" + "=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)
    print(f"Persons:              {len(new_db.persons)}")
    print(f"Places:               {len(new_db.places)}")
    print(f"Events:               {len(new_db.events)}")
    print(f"Event Participations: {len(new_db.event_participations)}")
    print(f"Family Relationships: {len(new_db.family_relationships)}")
    print("=" * 70)


def migrate_persons(old_persons, new_db):
    """Convert old person format to new person format"""
    for person_id, old_person in old_persons.items():
        # Convert birth year to FlexibleDate
        birth_date = None
        if old_person.get('birth_year_estimate'):
            birth_date = FlexibleDate(year=old_person['birth_year_estimate'], circa=True)

        # Convert death year to FlexibleDate
        death_date = None
        if old_person.get('death_year_estimate'):
            death_date = FlexibleDate(year=old_person['death_year_estimate'], circa=True)

        # Convert occupations list to single occupation string
        occupation = None
        if old_person.get('occupations'):
            occupation = ', '.join(old_person['occupations'])

        # Create new person
        new_person = Person(
            id=person_id,
            first_name=old_person.get('given_name', ''),
            last_name=old_person.get('surname', ''),
            maiden_name=old_person.get('maiden_name'),
            gender=old_person.get('gender', 'U'),
            birth_date=birth_date,
            death_date=death_date,
            occupation=occupation,
            tags=[],
            links=[],
            notes=None
        )

        new_db.persons[person_id] = new_person


def create_places(old_data, new_db):
    """Create place entities from old data"""
    place_set = set()  # Track unique places

    # Extract places from events
    for event in old_data.get('events', {}).values():
        if event.get('house_number'):
            place_key = (event.get('house_number'), 'Grzybowa Góra')
            place_set.add(place_key)

    # Extract places from persons (place_of_birth, place_of_death)
    for person in old_data.get('persons', {}).values():
        if person.get('place_of_birth'):
            place_key = (None, person['place_of_birth'])
            place_set.add(place_key)
        if person.get('place_of_death'):
            place_key = (None, person['place_of_death'])
            place_set.add(place_key)

    # Create Place objects
    place_counter = 1
    for house_number, name in place_set:
        place_id = f"PL{place_counter:04d}"
        place = Place(
            id=place_id,
            name=name,
            parish_name='Grzybowa Góra',  # Default parish
            house_number=house_number
        )
        new_db.places[place_id] = place
        place_counter += 1


def get_place_id(new_db, house_number=None, name=None):
    """Find or create a place ID for given location"""
    for place_id, place in new_db.places.items():
        if house_number and place.house_number == house_number:
            return place_id
        if name and place.name == name and not house_number:
            return place_id
    return None


def migrate_events(old_events, new_db):
    """Convert old event format to new event format"""
    for event_id, old_event in old_events.items():
        # Convert year to FlexibleDate
        event_date = None
        if old_event.get('year'):
            event_date = FlexibleDate(year=old_event['year'])

        # Get place_id
        place_id = get_place_id(new_db, old_event.get('house_number'))

        # Create new event
        new_event = Event(
            id=event_id,
            type=old_event.get('type', 'unknown'),
            date=event_date,
            place_id=place_id,
            content=old_event.get('original_text'),
            tags=[],
            links=[],
            notes=f"Source line: {old_event.get('source_line')}" if old_event.get('source_line') else None
        )

        new_db.events[event_id] = new_event


def create_event_participations(old_events, new_db):
    """Create EventParticipation records from old event structure"""
    ep_counter = 1

    for event_id, old_event in old_events.items():
        event_type = old_event.get('type')

        # Birth events
        if event_type == 'birth':
            # Child
            if old_event.get('child'):
                ep_id = f"EP{ep_counter:04d}"
                new_db.event_participations[ep_id] = EventParticipation(
                    id=ep_id,
                    event_id=event_id,
                    person_id=old_event['child'],
                    role='child'
                )
                ep_counter += 1

            # Father
            if old_event.get('father'):
                ep_id = f"EP{ep_counter:04d}"
                new_db.event_participations[ep_id] = EventParticipation(
                    id=ep_id,
                    event_id=event_id,
                    person_id=old_event['father'],
                    role='father'
                )
                ep_counter += 1

            # Mother
            if old_event.get('mother'):
                ep_id = f"EP{ep_counter:04d}"
                new_db.event_participations[ep_id] = EventParticipation(
                    id=ep_id,
                    event_id=event_id,
                    person_id=old_event['mother'],
                    role='mother'
                )
                ep_counter += 1

            # Witnesses
            for witness_id in old_event.get('witnesses', []):
                ep_id = f"EP{ep_counter:04d}"
                new_db.event_participations[ep_id] = EventParticipation(
                    id=ep_id,
                    event_id=event_id,
                    person_id=witness_id,
                    role='witness'
                )
                ep_counter += 1

            # Godparents
            for godparent_id in old_event.get('godparents', []):
                ep_id = f"EP{ep_counter:04d}"
                new_db.event_participations[ep_id] = EventParticipation(
                    id=ep_id,
                    event_id=event_id,
                    person_id=godparent_id,
                    role='godparent'
                )
                ep_counter += 1

        # Marriage events
        elif event_type == 'marriage':
            # Groom
            if old_event.get('groom'):
                ep_id = f"EP{ep_counter:04d}"
                new_db.event_participations[ep_id] = EventParticipation(
                    id=ep_id,
                    event_id=event_id,
                    person_id=old_event['groom'],
                    role='spouse'
                )
                ep_counter += 1

            # Bride
            if old_event.get('bride'):
                ep_id = f"EP{ep_counter:04d}"
                new_db.event_participations[ep_id] = EventParticipation(
                    id=ep_id,
                    event_id=event_id,
                    person_id=old_event['bride'],
                    role='spouse'
                )
                ep_counter += 1

            # Witnesses
            for witness_id in old_event.get('witnesses', []):
                ep_id = f"EP{ep_counter:04d}"
                new_db.event_participations[ep_id] = EventParticipation(
                    id=ep_id,
                    event_id=event_id,
                    person_id=witness_id,
                    role='witness'
                )
                ep_counter += 1

        # Death events
        elif event_type == 'death':
            # Deceased
            if old_event.get('deceased'):
                ep_id = f"EP{ep_counter:04d}"
                new_db.event_participations[ep_id] = EventParticipation(
                    id=ep_id,
                    event_id=event_id,
                    person_id=old_event['deceased'],
                    role='deceased'
                )
                ep_counter += 1

            # Witnesses
            for witness_id in old_event.get('witnesses', []):
                ep_id = f"EP{ep_counter:04d}"
                new_db.event_participations[ep_id] = EventParticipation(
                    id=ep_id,
                    event_id=event_id,
                    person_id=witness_id,
                    role='witness'
                )
                ep_counter += 1


def migrate_relationships(old_relationships, new_db):
    """Convert old relationship format to new family relationship format"""
    for rel_id, old_rel in old_relationships.items():
        rel_type = old_rel.get('type')

        # Map old relationship types to new types
        new_type = None
        person_1_id = old_rel['from_person']
        person_2_id = old_rel['to_person']

        if rel_type == 'biological_parent':
            # In old model: from_person is parent, to_person is child
            # In new model: use "parent" type, person_1 is parent, person_2 is child
            new_type = 'parent'
        elif rel_type == 'marriage':
            new_type = 'spouse'
        elif rel_type == 'godparent':
            # Keep as standalone - godparent is from_person, godchild is to_person
            continue  # Skip godparent relationships as they're captured in events

        if new_type:
            # Get source event from evidence if available
            source_event_id = None
            if old_rel.get('evidence') and len(old_rel['evidence']) > 0:
                source_event_id = old_rel['evidence'][0]

            new_rel = FamilyRelationship(
                id=rel_id,
                person_1_id=person_1_id,
                person_2_id=person_2_id,
                type=new_type,
                source_event_id=source_event_id
            )

            new_db.family_relationships[rel_id] = new_rel


if __name__ == '__main__':
    old_data_file = 'data/genealogy_complete.json'
    new_data_file = 'data/genealogy_new_model.json'

    if len(sys.argv) > 1:
        old_data_file = sys.argv[1]
    if len(sys.argv) > 2:
        new_data_file = sys.argv[2]

    try:
        migrate_old_to_new(old_data_file, new_data_file)
        print("\n✅ Migration completed successfully!")
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
