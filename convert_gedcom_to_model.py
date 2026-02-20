#!/usr/bin/env python3
"""
Convert GEDCOM file to event-based data model
Output: data/gedcom_model.json with same structure as genealogy_new_model.json
"""

import json
import re
from datetime import datetime

def parse_gedcom_date(date_str):
    """Parse GEDCOM date string to flexible date object"""
    if not date_str:
        return None

    # Remove common prefixes
    date_str = date_str.upper().replace('ABT', '').replace('EST', '').replace('CAL', '').strip()

    parts = date_str.split()
    date_obj = {'year': None, 'month': None, 'day': None, 'circa': 'ABT' in date_str or 'EST' in date_str}

    # Month mapping
    months = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
        'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }

    for part in parts:
        if part.isdigit():
            num = int(part)
            if num > 31:  # Likely a year
                date_obj['year'] = num
            else:  # Likely a day
                date_obj['day'] = num
        elif part in months:
            date_obj['month'] = months[part]

    return date_obj if date_obj['year'] else None

def get_next_id(existing_ids, prefix):
    """Generate next available ID"""
    max_num = 0
    for id_str in existing_ids:
        if id_str.startswith(prefix):
            try:
                num = int(id_str[len(prefix):])
                max_num = max(max_num, num)
            except ValueError:
                continue
    return f"{prefix}{max_num + 1:04d}"

def convert_gedcom_to_model(gedcom_path, output_path):
    """Convert GEDCOM to event-based model"""

    print(f"Reading GEDCOM file: {gedcom_path}")

    # Try different encodings
    content = None
    for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            with open(gedcom_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            print(f"  Successfully read with encoding: {encoding}")
            break
        except:
            continue

    if not content:
        raise Exception("Could not read GEDCOM file with any encoding")

    lines = content.split('\n')

    # Data structures
    gedcom_persons = {}  # Temporary storage with GEDCOM IDs
    gedcom_families = {}
    persons = {}
    events = {}
    event_participations = {}
    places = {}

    # Parse individuals
    print("\nParsing individuals...")
    current_person = None
    current_event_type = None

    for line in lines:
        if not line.strip() or not line[0].isdigit():
            continue

        parts = line.strip().split(None, 2)
        if len(parts) < 2:
            continue

        level = parts[0]
        tag = parts[1]
        value = parts[2] if len(parts) > 2 else ''

        # Start of individual
        if level == '0' and tag.startswith('@I') and 'INDI' in value:
            if current_person:
                gedcom_persons[current_person['gedcom_id']] = current_person
            current_person = {
                'gedcom_id': tag,
                'birth': {},
                'death': {},
                'families_spouse': [],
                'families_child': []
            }
            current_event_type = None

        elif level == '0' and tag.startswith('@F') and 'FAM' in value:
            # Family record - we'll parse these separately
            pass

        elif level == '0':
            if current_person:
                gedcom_persons[current_person['gedcom_id']] = current_person
                current_person = None

        elif current_person:
            if level == '1':
                current_event_type = None

                if tag == 'NAME':
                    name_parts = value.replace('/', '').strip().split()
                    if len(name_parts) >= 1:
                        current_person['first_name'] = name_parts[0]
                    if len(name_parts) >= 2:
                        current_person['last_name'] = ' '.join(name_parts[1:])

                elif tag == 'SEX':
                    current_person['gender'] = 'M' if value == 'M' else 'F' if value == 'F' else 'U'

                elif tag == 'BIRT':
                    current_event_type = 'birth'

                elif tag == 'DEAT':
                    current_event_type = 'death'

                elif tag == 'FAMS':
                    current_person['families_spouse'].append(value.strip())

                elif tag == 'FAMC':
                    current_person['families_child'].append(value.strip())

            elif level == '2' and current_event_type:
                if tag == 'DATE':
                    current_person[current_event_type]['date'] = parse_gedcom_date(value)

                elif tag == 'PLAC':
                    current_person[current_event_type]['place_name'] = value.strip()

    # Save last person
    if current_person:
        gedcom_persons[current_person['gedcom_id']] = current_person

    print(f"  Found {len(gedcom_persons)} individuals")

    # Parse families
    print("\nParsing families...")
    current_family = None

    for line in lines:
        if not line.strip() or not line[0].isdigit():
            continue

        parts = line.strip().split(None, 2)
        if len(parts) < 2:
            continue

        level = parts[0]
        tag = parts[1]
        value = parts[2] if len(parts) > 2 else ''

        if level == '0' and tag.startswith('@F') and 'FAM' in value:
            if current_family:
                gedcom_families[current_family['gedcom_id']] = current_family
            current_family = {
                'gedcom_id': tag,
                'husband': None,
                'wife': None,
                'children': [],
                'marriage': {}
            }

        elif level == '0':
            if current_family:
                gedcom_families[current_family['gedcom_id']] = current_family
                current_family = None

        elif current_family and level == '1':
            if tag == 'HUSB':
                current_family['husband'] = value.strip()
            elif tag == 'WIFE':
                current_family['wife'] = value.strip()
            elif tag == 'CHIL':
                current_family['children'].append(value.strip())
            elif tag == 'MARR':
                current_family['_reading_marriage'] = True

        elif current_family and level == '2' and current_family.get('_reading_marriage'):
            if tag == 'DATE':
                current_family['marriage']['date'] = parse_gedcom_date(value)
            elif tag == 'PLAC':
                current_family['marriage']['place_name'] = value.strip()

    if current_family:
        gedcom_families[current_family['gedcom_id']] = current_family

    print(f"  Found {len(gedcom_families)} families")

    # Convert to our model
    print("\nConverting to event-based model...")

    # Create persons with new IDs
    gedcom_to_new_id = {}  # Map GEDCOM IDs to new IDs
    person_id_counter = 0

    for gedcom_id, gedcom_person in gedcom_persons.items():
        person_id_counter += 1
        new_id = f"G{person_id_counter:04d}"  # G prefix for GEDCOM persons
        gedcom_to_new_id[gedcom_id] = new_id

        persons[new_id] = {
            'id': new_id,
            'first_name': gedcom_person.get('first_name', ''),
            'last_name': gedcom_person.get('last_name', ''),
            'maiden_name': None,
            'gender': gedcom_person.get('gender', 'U'),
            'birth_date': gedcom_person.get('birth', {}).get('date'),
            'death_date': gedcom_person.get('death', {}).get('date'),
            'occupation': None
        }

    print(f"  Converted {len(persons)} persons")

    # Create events
    event_id_counter = 0
    ep_id_counter = 0
    place_id_counter = 0

    # Birth events
    for gedcom_id, gedcom_person in gedcom_persons.items():
        birth_data = gedcom_person.get('birth', {})
        if birth_data.get('date') or birth_data.get('place_name'):
            event_id_counter += 1
            event_id = f"GE{event_id_counter:04d}"

            # Handle place
            place_id = None
            if birth_data.get('place_name'):
                place_name = birth_data['place_name']
                # Find or create place
                existing_place = next((pid for pid, p in places.items() if p['name'] == place_name), None)
                if existing_place:
                    place_id = existing_place
                else:
                    place_id_counter += 1
                    place_id = f"GPL{place_id_counter:04d}"
                    places[place_id] = {
                        'id': place_id,
                        'name': place_name,
                        'house_number': ''
                    }

            events[event_id] = {
                'id': event_id,
                'type': 'birth',
                'date': birth_data.get('date'),
                'place_id': place_id,
                'content': f"Birth from GEDCOM",
                'source': 'gedcom'
            }

            # Add child participation
            ep_id_counter += 1
            ep_id = f"GEP{ep_id_counter:04d}"
            event_participations[ep_id] = {
                'id': ep_id,
                'event_id': event_id,
                'person_id': gedcom_to_new_id[gedcom_id],
                'role': 'child'
            }

    # Death events
    for gedcom_id, gedcom_person in gedcom_persons.items():
        death_data = gedcom_person.get('death', {})
        if death_data.get('date') or death_data.get('place_name'):
            event_id_counter += 1
            event_id = f"GE{event_id_counter:04d}"

            # Handle place
            place_id = None
            if death_data.get('place_name'):
                place_name = death_data['place_name']
                existing_place = next((pid for pid, p in places.items() if p['name'] == place_name), None)
                if existing_place:
                    place_id = existing_place
                else:
                    place_id_counter += 1
                    place_id = f"GPL{place_id_counter:04d}"
                    places[place_id] = {
                        'id': place_id,
                        'name': place_name,
                        'house_number': ''
                    }

            events[event_id] = {
                'id': event_id,
                'type': 'death',
                'date': death_data.get('date'),
                'place_id': place_id,
                'content': f"Death from GEDCOM",
                'source': 'gedcom'
            }

            # Add deceased participation
            ep_id_counter += 1
            ep_id = f"GEP{ep_id_counter:04d}"
            event_participations[ep_id] = {
                'id': ep_id,
                'event_id': event_id,
                'person_id': gedcom_to_new_id[gedcom_id],
                'role': 'deceased'
            }

    # Marriage events and parent-child relationships from families
    for family_id, family in gedcom_families.items():
        # Marriage event
        if family.get('marriage', {}).get('date') or family.get('marriage', {}).get('place_name'):
            husband_id = gedcom_to_new_id.get(family.get('husband'))
            wife_id = gedcom_to_new_id.get(family.get('wife'))

            if husband_id or wife_id:
                event_id_counter += 1
                event_id = f"GE{event_id_counter:04d}"

                # Handle place
                place_id = None
                marriage_data = family.get('marriage', {})
                if marriage_data.get('place_name'):
                    place_name = marriage_data['place_name']
                    existing_place = next((pid for pid, p in places.items() if p['name'] == place_name), None)
                    if existing_place:
                        place_id = existing_place
                    else:
                        place_id_counter += 1
                        place_id = f"GPL{place_id_counter:04d}"
                        places[place_id] = {
                            'id': place_id,
                            'name': place_name,
                            'house_number': ''
                        }

                events[event_id] = {
                    'id': event_id,
                    'type': 'marriage',
                    'date': marriage_data.get('date'),
                    'place_id': place_id,
                    'content': f"Marriage from GEDCOM",
                    'source': 'gedcom'
                }

                # Add spouses
                if husband_id:
                    ep_id_counter += 1
                    ep_id = f"GEP{ep_id_counter:04d}"
                    event_participations[ep_id] = {
                        'id': ep_id,
                        'event_id': event_id,
                        'person_id': husband_id,
                        'role': 'groom'
                    }

                if wife_id:
                    ep_id_counter += 1
                    ep_id = f"GEP{ep_id_counter:04d}"
                    event_participations[ep_id] = {
                        'id': ep_id,
                        'event_id': event_id,
                        'person_id': wife_id,
                        'role': 'bride'
                    }

        # Create birth events for children with parents
        for child_gedcom_id in family.get('children', []):
            child_id = gedcom_to_new_id.get(child_gedcom_id)
            if not child_id:
                continue

            # Find child's birth event
            child_birth_event = None
            for ep in event_participations.values():
                if ep['person_id'] == child_id and ep['role'] == 'child':
                    child_birth_event = ep['event_id']
                    break

            # If no birth event, create one
            if not child_birth_event:
                event_id_counter += 1
                child_birth_event = f"GE{event_id_counter:04d}"
                events[child_birth_event] = {
                    'id': child_birth_event,
                    'type': 'birth',
                    'date': None,
                    'place_id': None,
                    'content': f"Birth from GEDCOM family",
                    'source': 'gedcom'
                }

                # Add child
                ep_id_counter += 1
                ep_id = f"GEP{ep_id_counter:04d}"
                event_participations[ep_id] = {
                    'id': ep_id,
                    'event_id': child_birth_event,
                    'person_id': child_id,
                    'role': 'child'
                }

            # Add parents to birth event
            husband_id = gedcom_to_new_id.get(family.get('husband'))
            wife_id = gedcom_to_new_id.get(family.get('wife'))

            if husband_id:
                ep_id_counter += 1
                ep_id = f"GEP{ep_id_counter:04d}"
                event_participations[ep_id] = {
                    'id': ep_id,
                    'event_id': child_birth_event,
                    'person_id': husband_id,
                    'role': 'father'
                }

            if wife_id:
                ep_id_counter += 1
                ep_id = f"GEP{ep_id_counter:04d}"
                event_participations[ep_id] = {
                    'id': ep_id,
                    'event_id': child_birth_event,
                    'person_id': wife_id,
                    'role': 'mother'
                }

    print(f"  Created {len(events)} events")
    print(f"  Created {len(event_participations)} event participations")
    print(f"  Created {len(places)} places")

    # Build output data structure
    output_data = {
        'persons': persons,
        'places': places,
        'events': events,
        'event_participations': event_participations,
        'metadata': {
            'source': 'GEDCOM conversion',
            'original_file': gedcom_path,
            'total_persons': len(persons),
            'total_events': len(events),
            'total_relationships': 0,  # Derived from events
            'converted_at': datetime.now().isoformat()
        }
    }

    # Save to file
    print(f"\nSaving to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✓ Conversion complete!")
    print(f"\nSummary:")
    print(f"  Persons: {len(persons)}")
    print(f"  Events: {len(events)}")
    print(f"  Event participations: {len(event_participations)}")
    print(f"  Places: {len(places)}")

    return output_data

if __name__ == '__main__':
    convert_gedcom_to_model('base.ged', 'data/gedcom_model.json')
