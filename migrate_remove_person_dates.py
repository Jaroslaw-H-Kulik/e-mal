#!/usr/bin/env python3
"""
Migration: Remove birth_date / death_date from person records.

If a person has these fields but no corresponding birth/death event,
a new event is created from the person's data.
If an event already exists, event data prevails (person field just removed).
"""
import json


def get_next_event_id(events):
    if not events:
        return 'E0001'
    max_id = max([int(e['id'][1:]) for e in events.values()], default=0)
    return f'E{(max_id + 1):04d}'


def get_next_ep_id(event_participations):
    if not event_participations:
        return 'EP0001'
    max_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)
    return f'EP{(max_id + 1):04d}'


data_path = 'data/genealogy_new_model.json'
with open(data_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

persons = data['persons']
events = data['events']
event_participations = data.get('event_participations', {})

# Build index: person_id -> birth/death event id
person_birth_events = {}
person_death_events = {}

for ep in event_participations.values():
    event = events.get(ep['event_id'])
    if not event:
        continue
    if ep['role'] == 'child' and event['type'] in ('birth', 'baptism'):
        person_birth_events[ep['person_id']] = ep['event_id']
    elif ep['role'] == 'deceased' and event['type'] in ('death', 'burial'):
        person_death_events[ep['person_id']] = ep['event_id']

created_events = 0
removed_birth = 0
removed_death = 0

for person_id, person in persons.items():
    name = f"{person.get('first_name', '')} {person.get('last_name', '')}"

    # Handle birth_date
    if person.get('birth_date'):
        if person_id not in person_birth_events:
            # No birth event exists — create one from person data
            event_id = get_next_event_id(events)
            events[event_id] = {
                'id': event_id,
                'type': 'birth',
                'date': person['birth_date'],
                'place_id': None,
                'content': f'Birth of {name.strip()}',
                'tags': [],
                'links': [],
                'notes': 'Migrated from person model (step 56.1)'
            }
            ep_id = get_next_ep_id(event_participations)
            event_participations[ep_id] = {
                'id': ep_id,
                'event_id': event_id,
                'person_id': person_id,
                'role': 'child'
            }
            person_birth_events[person_id] = event_id
            created_events += 1
            print(f'  Created birth event {event_id} for {person_id} ({name.strip()}) date={person["birth_date"]}')
        else:
            print(f'  {person_id}: birth event already exists ({person_birth_events[person_id]}), event prevails')
        del person['birth_date']
        removed_birth += 1

    # Handle death_date
    if person.get('death_date'):
        if person_id not in person_death_events:
            # No death event exists — create one from person data
            event_id = get_next_event_id(events)
            events[event_id] = {
                'id': event_id,
                'type': 'death',
                'date': person['death_date'],
                'place_id': None,
                'content': f'Death of {name.strip()}',
                'tags': [],
                'links': [],
                'notes': 'Migrated from person model (step 56.1)'
            }
            ep_id = get_next_ep_id(event_participations)
            event_participations[ep_id] = {
                'id': ep_id,
                'event_id': event_id,
                'person_id': person_id,
                'role': 'deceased'
            }
            person_death_events[person_id] = event_id
            created_events += 1
            print(f'  Created death event {event_id} for {person_id} ({name.strip()}) date={person["death_date"]}')
        else:
            print(f'  {person_id}: death event already exists ({person_death_events[person_id]}), event prevails')
        del person['death_date']
        removed_death += 1

data['event_participations'] = event_participations

with open(data_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'\nMigration complete:')
print(f'  Removed birth_date from {removed_birth} persons')
print(f'  Removed death_date from {removed_death} persons')
print(f'  Created {created_events} new events from orphaned person dates')
