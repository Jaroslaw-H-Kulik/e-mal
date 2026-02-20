#!/usr/bin/env python3
"""
Migration script to make relationships purely event-based.
Creates birth and marriage events for relationships that don't have corresponding events.
"""

import json
from datetime import datetime

def get_next_id(existing_ids, prefix):
    """Generate next available ID with given prefix"""
    max_num = 0
    for id_str in existing_ids:
        if id_str.startswith(prefix):
            try:
                num = int(id_str[len(prefix):])
                max_num = max(max_num, num)
            except ValueError:
                continue
    return f"{prefix}{max_num + 1:04d}"

def main():
    # Load data
    print("Loading data from genealogy_new_model.json...")
    with open('data/genealogy_new_model.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    persons = data['persons']
    events = data['events']
    event_participations = data['event_participations']
    family_relationships = data['family_relationships']
    places = data.get('places', {})

    print(f"Loaded: {len(persons)} persons, {len(events)} events, {len(event_participations)} participations")
    print(f"Loaded: {len(family_relationships)} family relationships")
    print()

    # Build event participation index
    person_events = {}
    for ep_id, ep in event_participations.items():
        person_id = ep['person_id']
        event_id = ep['event_id']
        role = ep['role']

        if person_id not in person_events:
            person_events[person_id] = []
        person_events[person_id].append({
            'event_id': event_id,
            'role': role,
            'event': events[event_id]
        })

    new_events = {}
    new_participations = {}

    # Process parent relationships
    print("Processing parent relationships...")
    parent_rels_without_events = []

    for rel_id, rel in family_relationships.items():
        if rel['type'] == 'parent':
            parent_id = rel['person_1_id']
            child_id = rel['person_2_id']

            # Check if child has a birth event with this parent
            has_event = False
            if child_id in person_events:
                for ep in person_events[child_id]:
                    if ep['role'] == 'child' and ep['event']['type'] == 'birth':
                        # Check if parent participates in this event
                        event_participants = [e for e in event_participations.values() if e['event_id'] == ep['event_id']]
                        parent_roles = [e['person_id'] for e in event_participants if e['role'] in ['father', 'mother']]
                        if parent_id in parent_roles:
                            has_event = True
                            break

            if not has_event:
                parent_rels_without_events.append((parent_id, child_id, rel_id))

    print(f"Found {len(parent_rels_without_events)} parent relationships without birth events")

    # Group parent relationships by child to create one birth event per child
    children_parents = {}
    for parent_id, child_id, rel_id in parent_rels_without_events:
        if child_id not in children_parents:
            children_parents[child_id] = []
        children_parents[child_id].append(parent_id)

    print(f"Creating birth events for {len(children_parents)} children...")

    for child_id, parent_ids in children_parents.items():
        child = persons[child_id]

        # Create birth event
        event_id = get_next_id(list(events.keys()) + list(new_events.keys()), 'E')

        # Try to get birth year from child's birth_date
        birth_year = None
        if child.get('birth_date') and child['birth_date'].get('year'):
            birth_year = child['birth_date']['year']

        event_data = {
            'id': event_id,
            'type': 'birth',
            'date': {
                'year': birth_year,
                'month': None,
                'day': None,
                'circa': True
            } if birth_year else None,
            'place_id': None,
            'content': f"Birth of {child.get('first_name', '')} {child.get('last_name', '')} (synthetic event from migration)",
            'source': 'migration_synthetic'
        }

        new_events[event_id] = event_data

        # Add child participation
        ep_id = get_next_id(list(event_participations.keys()) + list(new_participations.keys()), 'EP')
        new_participations[ep_id] = {
            'id': ep_id,
            'event_id': event_id,
            'person_id': child_id,
            'role': 'child'
        }

        # Add parent participations
        for parent_id in parent_ids:
            parent = persons[parent_id]
            role = 'father' if parent.get('gender') == 'M' else 'mother'

            ep_id = get_next_id(list(event_participations.keys()) + list(new_participations.keys()), 'EP')
            new_participations[ep_id] = {
                'id': ep_id,
                'event_id': event_id,
                'person_id': parent_id,
                'role': role
            }

    print(f"Created {len(children_parents)} birth events with {len([p for p in new_participations.values() if events.get(p['event_id']) or new_events.get(p['event_id'])])} participations")
    print()

    # Process spouse relationships
    print("Processing spouse relationships...")
    spouse_rels_without_events = []

    for rel_id, rel in family_relationships.items():
        if rel['type'] == 'spouse':
            person_1_id = rel['person_1_id']
            person_2_id = rel['person_2_id']

            # Check if there's a marriage event between these two
            has_event = False
            if person_1_id in person_events:
                for ep in person_events[person_1_id]:
                    if ep['event']['type'] == 'marriage':
                        event_participants = [e for e in event_participations.values() if e['event_id'] == ep['event_id']]
                        spouse_ids = [e['person_id'] for e in event_participants if e['role'] in ['groom', 'bride']]
                        if person_2_id in spouse_ids:
                            has_event = True
                            break

            if not has_event:
                spouse_rels_without_events.append((person_1_id, person_2_id, rel_id))

    print(f"Found {len(spouse_rels_without_events)} spouse relationships without marriage events")
    print(f"Creating marriage events...")

    for person_1_id, person_2_id, rel_id in spouse_rels_without_events:
        person_1 = persons[person_1_id]
        person_2 = persons[person_2_id]

        # Create marriage event
        event_id = get_next_id(list(events.keys()) + list(new_events.keys()), 'E')

        # Try to estimate marriage year from birth dates
        marriage_year = None
        if person_1.get('birth_date') and person_1['birth_date'].get('year'):
            marriage_year = person_1['birth_date']['year'] + 25  # Rough estimate
        elif person_2.get('birth_date') and person_2['birth_date'].get('year'):
            marriage_year = person_2['birth_date']['year'] + 25

        event_data = {
            'id': event_id,
            'type': 'marriage',
            'date': {
                'year': marriage_year,
                'month': None,
                'day': None,
                'circa': True
            } if marriage_year else None,
            'place_id': None,
            'content': f"Marriage of {person_1.get('first_name', '')} {person_1.get('last_name', '')} and {person_2.get('first_name', '')} {person_2.get('last_name', '')} (synthetic event from migration)",
            'source': 'migration_synthetic'
        }

        new_events[event_id] = event_data

        # Add groom participation (person_1 if male, otherwise person_2)
        groom_id = person_1_id if person_1.get('gender') == 'M' else person_2_id
        bride_id = person_2_id if groom_id == person_1_id else person_1_id

        ep_id = get_next_id(list(event_participations.keys()) + list(new_participations.keys()), 'EP')
        new_participations[ep_id] = {
            'id': ep_id,
            'event_id': event_id,
            'person_id': groom_id,
            'role': 'groom'
        }

        ep_id = get_next_id(list(event_participations.keys()) + list(new_participations.keys()), 'EP')
        new_participations[ep_id] = {
            'id': ep_id,
            'event_id': event_id,
            'person_id': bride_id,
            'role': 'bride'
        }

    print(f"Created {len(spouse_rels_without_events)} marriage events")
    print()

    # Merge new events and participations into data
    events.update(new_events)
    event_participations.update(new_participations)

    print("Summary:")
    print(f"  Total events: {len(events)} (added {len(new_events)})")
    print(f"  Total participations: {len(event_participations)} (added {len(new_participations)})")
    print()

    # Update metadata
    data['metadata']['total_events'] = len(events)
    data['metadata']['last_updated'] = datetime.now().isoformat()
    data['metadata']['migration_note'] = 'Migrated to event-based relationships'

    # Save updated data
    output_file = 'data/genealogy_new_model.json'
    print(f"Saving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Migration complete!")
    print()
    print("Next step: Remove family_relationships from data model")

if __name__ == '__main__':
    main()
