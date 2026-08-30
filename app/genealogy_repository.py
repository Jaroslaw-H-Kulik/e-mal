"""
Data access + business logic for data/genealogy_new_model.json: persons,
events, event participations, and places. No HTTP awareness -
GenealogyServerHandler (server.py) delegates to a module-level instance of
this class and just serializes whatever it returns.
"""
import json


class GenealogyRepository:

    def get_data_path(self):
        return 'data/genealogy_new_model.json'

    def load_data(self):
        with open(self.get_data_path(), 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data

    def save_data(self, data):
        with open(self.get_data_path(), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_genealogy_data(self, data):
        """Save complete genealogy data to data/genealogy_new_model.json"""
        self.save_data(data)

        print(f"[OK] Saved genealogy data: {len(data.get('persons', {}))} persons")

    def get_next_person_id(self, persons):
        """Generate next person ID"""
        max_id = max([int(p['id'][1:]) for p in persons.values()], default=0)
        return f"P{(max_id + 1):04d}"

    def get_next_event_id(self, events):
        """Generate next event ID"""
        max_id = max([int(e['id'][1:]) for e in events.values()], default=0)
        return f"E{(max_id + 1):04d}"

    def get_next_event_participation_id(self, event_participations):
        """Generate next event participation ID"""
        if not event_participations:
            return "EP0001"
        max_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)
        return f"EP{(max_id + 1):04d}"

    def determine_parent_role(self, person):
        """Determine parent role based on gender"""
        return 'father' if person.get('gender') == 'M' else 'mother'

    def resolve_place(self, places, place_name, house_number=None):
        """Find an existing place or create a new one.

        house_number=None (add_person/update_person callers): match by name
        only, case-insensitive, and create a place with no house_number field.
        house_number='' or a real value (add_event/update_event via
        handle_place): match by name (case-sensitive) AND house_number, and
        create a place with a house_number field. The two call sites had
        independently-duplicated, slightly different matching rules before
        this was unified - preserved as-is rather than reconciled, since
        changing either would change which existing places get reused.
        """
        for place_id, place in places.items():
            if house_number is None:
                if place.get('name', '').lower() == place_name.lower():
                    return place_id
            elif place.get('name') == place_name and place.get('house_number', '') == house_number:
                return place_id

        max_id = max([int(p['id'][2:]) for p in places.values()], default=0) if places else 0
        new_place_id = f"PL{(max_id + 1):04d}"
        if house_number is None:
            # Canonical field set/order (normalize_data_schema.py) - written
            # here so add_person/update_person keep producing the same closed
            # shape as the normalized data file, rather than reintroducing
            # missing-key drift on every new place (see JAVA_MIGRATION.md's
            # Phase 0 addendum, and the golden-fixture regen this required).
            places[new_place_id] = {
                'id': new_place_id,
                'name': place_name,
                'parish_name': None,
                'house_number': None,
                'type': 'settlement'
            }
        else:
            # Same canonical-shape fix as the house_number-is-None branch
            # above (parish_name/type as null) - see JAVA_MIGRATION.md's
            # `resolve_place` Phase 0 addendum, closed for this branch
            # while porting step 3 (add-event).
            places[new_place_id] = {
                'id': new_place_id,
                'name': place_name,
                'parish_name': None,
                'house_number': house_number,
                'type': None
            }
        print(f"  [OK] Created new place: {new_place_id} - {place_name}")
        return new_place_id

    def handle_place(self, places, event_data):
        if not event_data.get('place_name'):
            return None
        return self.resolve_place(places, event_data['place_name'], event_data.get('house_number', ''))

    def normalize_date(self, date_value):
        """Ensures a date dict always carries all four canonical keys
        (year/month/day = None if absent, circa = False if absent), the
        same shape normalize_data_schema.py's DATE_FIELDS pass enforces at
        rest. add_event/update_event store event_data['date'] as sent by
        the client, which (e.g. web/event-editor.js) omits 'circa'
        entirely - closed here for add_event while porting step 3, and for
        update_event while porting step 4, so Python and Java write the
        same shape going forward. Returns None unchanged."""
        if date_value is None:
            return None
        return {
            'year': date_value.get('year'),
            'month': date_value.get('month'),
            'day': date_value.get('day'),
            'circa': bool(date_value.get('circa', False)),
        }

    def find_birth_event_for_person(self, events, event_participations, person_id):
        """Find birth event where person is the child"""
        for ep in event_participations.values():
            if ep['person_id'] == person_id and ep['role'] == 'child':
                event = events.get(ep['event_id'])
                if event and event['type'] == 'birth':
                    return ep['event_id']
        return None

    def find_death_event_for_person(self, events, event_participations, person_id):
        """Find death event where person is deceased"""
        for ep in event_participations.values():
            if ep['person_id'] == person_id and ep['role'] == 'deceased':
                event = events.get(ep['event_id'])
                if event and event['type'] == 'death':
                    return ep['event_id']
        return None

    def find_marriage_event_between(self, events, event_participations, person1_id, person2_id):
        """Find marriage event between two people"""
        # Find all marriage events where person1 participates
        person1_marriages = []
        for ep in event_participations.values():
            if ep['person_id'] == person1_id and ep['role'] in ['groom', 'bride']:
                event = events.get(ep['event_id'])
                if event and event['type'] == 'marriage':
                    person1_marriages.append(ep['event_id'])

        # Check if person2 is in any of these marriages
        for event_id in person1_marriages:
            for ep in event_participations.values():
                if ep['event_id'] == event_id and ep['person_id'] == person2_id and ep['role'] in ['groom', 'bride']:
                    return event_id

        return None

    def create_parent_marriage_if_needed(self, events, event_participations, birth_event_id, persons):
        """Step 13: Auto-create marriage event between parents if both present in birth event"""
        # Find both parents in this birth event
        father_id = None
        mother_id = None

        for ep in event_participations.values():
            if ep['event_id'] == birth_event_id:
                if ep['role'] == 'father':
                    father_id = ep['person_id']
                elif ep['role'] == 'mother':
                    mother_id = ep['person_id']

        # If both parents present, check if marriage exists
        if father_id and mother_id:
            existing_marriage = self.find_marriage_event_between(events, event_participations, father_id, mother_id)

            if not existing_marriage:
                # Create marriage event
                marriage_event_id = self.get_next_event_id(events)
                father = persons[father_id]
                mother = persons[mother_id]

                events[marriage_event_id] = {
                    'id': marriage_event_id,
                    'type': 'marriage',
                    'date': None,
                    'place_id': None,
                    'content': '',
                    'description': f"Marriage of {father['first_name']} {father['last_name']} and {mother['first_name']} {mother['last_name']}",
                    'title': None,
                    'source': None,
                    'notes': f'Auto-generated from birth event {birth_event_id} (Step 30)',
                    'tags': [],
                    'links': []
                }

                # Add both parents as participants
                for person_id, role in [(father_id, 'groom'), (mother_id, 'bride')]:
                    ep_id = self.get_next_event_participation_id(event_participations)
                    event_participations[ep_id] = {
                        'id': ep_id,
                        'event_id': marriage_event_id,
                        'person_id': person_id,
                        'role': role
                    }

                print(f"  [OK] Step 13: Auto-created parent marriage event: {marriage_event_id}")
                return marriage_event_id

        return None

    def add_person(self, person_data):
        """Add a new person to the genealogy data with auto-created events (Step 9)"""
        try:
            data = self.load_data()

            persons = data['persons']
            places = data.get('places', {})
            events = data['events']
            event_participations = data.get('event_participations', {})

            # Generate new person ID
            new_id = self.get_next_person_id(persons)

            # Create person object with NEW model fields
            new_person = {
                'id': new_id,
                'first_name': person_data.get('given_name', ''),
                'last_name': person_data.get('surname', ''),
                'gender': person_data.get('gender', 'U'),
                'maiden_name': person_data.get('maiden_name'),
                'occupation': person_data.get('occupation', person_data.get('occupations')),
                'tags': person_data.get('tags', []),
                'notes': person_data.get('notes') or None
            }

            # Handle birth date (used for event creation only, not stored on person)
            birth_date = None
            if person_data.get('birth_year_estimate'):
                birth_date = {'year': person_data['birth_year_estimate'], 'month': None, 'day': None, 'circa': True}

            # Handle death date (used for event creation only, not stored on person)
            death_date = None
            if person_data.get('death_year_estimate'):
                death_date = {'year': person_data['death_year_estimate'], 'month': None, 'day': None, 'circa': True}

            # Add person to data
            persons[new_id] = new_person

            # Step 9: ALWAYS create birth event for every person
            created_events = []
            birth_event_id = self.get_next_event_id(events)

            # Handle place
            place_id = None
            if person_data.get('place_of_birth'):
                place_id = self.resolve_place(places, person_data['place_of_birth'])

            # Canonical field set/order (normalize_data_schema.py) - see
            # JAVA_MIGRATION.md's `resolve_place`/event-shape addendum: a
            # typed Java Event always serializes every field, so this must
            # write the full canonical shape (content/title/source as null)
            # rather than omitting keys, or step 2's port can't round-trip.
            birth_event = {
                'id': birth_event_id,
                'type': 'birth',
                'date': birth_date,
                'place_id': place_id,
                'content': None,
                'description': f"Birth of {new_person['first_name']} {new_person['last_name']}",
                'title': None,
                'source': None,
                'notes': 'Auto-generated from person creation',
                'tags': [],
                'links': []
            }
            events[birth_event_id] = birth_event

            # Create event participation (person as child)
            ep_id = self.get_next_event_participation_id(event_participations)
            event_participations[ep_id] = {
                'id': ep_id,
                'event_id': birth_event_id,
                'person_id': new_id,
                'role': 'child'
            }
            created_events.append(birth_event_id)
            print(f"  [OK] Auto-created birth event: {birth_event_id}")

            # Step 9: Auto-create death event if death data available
            if death_date or person_data.get('place_of_death'):
                death_event_id = self.get_next_event_id(events)

                # Handle place
                place_id = None
                if person_data.get('place_of_death'):
                    place_id = self.resolve_place(places, person_data['place_of_death'])

                death_event = {
                    'id': death_event_id,
                    'type': 'death',
                    'date': death_date,
                    'place_id': place_id,
                    'content': None,
                    'description': f"Death of {new_person['first_name']} {new_person['last_name']}",
                    'title': None,
                    'source': None,
                    'notes': 'Auto-generated from person creation',
                    'tags': [],
                    'links': []
                }
                events[death_event_id] = death_event

                # Create event participation (person as deceased)
                ep_id = self.get_next_event_participation_id(event_participations)
                event_participations[ep_id] = {
                    'id': ep_id,
                    'event_id': death_event_id,
                    'person_id': new_id,
                    'role': 'deceased'
                }
                created_events.append(death_event_id)
                print(f"  [OK] Auto-created death event: {death_event_id}")

            # Update data structure
            data['places'] = places

            self.save_data(data)

            print(f"[OK] Added new person: {new_id} - {new_person['first_name']} {new_person['last_name']}")
            if created_events:
                print(f"  Created {len(created_events)} event(s): {', '.join(created_events)}")

            created_event_set = set(created_events)
            return {
                'success': True,
                'person': new_person,
                'created_events': created_events,
                'new_events': {eid: events[eid] for eid in created_events},
                'new_participations': {epid: ep for epid, ep in event_participations.items()
                                       if ep['event_id'] in created_event_set},
                'message': f'Successfully added person {new_id}'
            }

        except Exception as e:
            print(f"[ERR] Error adding person: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def update_person(self, person_data):
        """Update person and sync to events (Step 9 bidirectional sync)"""
        try:
            data = self.load_data()

            persons = data['persons']
            places = data.get('places', {})
            events = data['events']
            event_participations = data.get('event_participations', {})

            person_id = person_data.get('person_id')
            if not person_id or person_id not in persons:
                return {'success': False, 'error': 'Person not found'}

            person = persons[person_id]
            updated_events = []

            # Update person fields
            if 'first_name' in person_data:
                person['first_name'] = person_data['first_name']
            if 'last_name' in person_data:
                person['last_name'] = person_data['last_name']
            if 'maiden_name' in person_data:
                person['maiden_name'] = person_data['maiden_name']
            if 'gender' in person_data:
                person['gender'] = person_data['gender']
            if 'occupation' in person_data:
                person['occupation'] = person_data['occupation']
            # Step 56: tags and notes
            if 'tags' in person_data:
                person['tags'] = person_data['tags'] if isinstance(person_data['tags'], list) else []
            if 'notes' in person_data:
                person['notes'] = person_data['notes'] or None

            # Handle birth date/place update - sync to birth event
            if 'birth_date' in person_data or 'place_of_birth' in person_data:
                birth_event_id = self.find_birth_event_for_person(events, event_participations, person_id)

                if birth_event_id:
                    # Update existing birth event
                    if 'birth_date' in person_data and person_data['birth_date']:
                        events[birth_event_id]['date'] = person_data['birth_date']
                        print(f"  [OK] Synced birth date to event {birth_event_id}")

                    if 'place_of_birth' in person_data and person_data['place_of_birth']:
                        place_id = self.resolve_place(places, person_data['place_of_birth'])
                        events[birth_event_id]['place_id'] = place_id
                        print(f"  [OK] Synced birth place to event {birth_event_id}")

                    updated_events.append(birth_event_id)
                else:
                    # Create birth event if data provided
                    if person_data.get('birth_date') or person_data.get('place_of_birth'):
                        birth_event_id = self.get_next_event_id(events)

                        place_id = None
                        if person_data.get('place_of_birth'):
                            place_id = self.resolve_place(places, person_data['place_of_birth'])

                        events[birth_event_id] = {
                            'id': birth_event_id,
                            'type': 'birth',
                            'date': person_data.get('birth_date'),
                            'place_id': place_id,
                            'content': None,
                            'description': f"Birth of {person['first_name']} {person['last_name']}",
                            'title': None,
                            'source': None,
                            'notes': 'Auto-generated from person update',
                            'tags': [],
                            'links': []
                        }

                        # Add person as child
                        ep_id = self.get_next_event_participation_id(event_participations)
                        event_participations[ep_id] = {
                            'id': ep_id,
                            'event_id': birth_event_id,
                            'person_id': person_id,
                            'role': 'child'
                        }

                        updated_events.append(birth_event_id)
                        print(f"  [OK] Created birth event: {birth_event_id}")

            # Handle death date/place update - sync to death event
            if 'death_date' in person_data or 'place_of_death' in person_data:
                print(f"  -> Processing death data: date={person_data.get('death_date')}, place={person_data.get('place_of_death')}")
                death_event_id = self.find_death_event_for_person(events, event_participations, person_id)
                print(f"  -> Existing death event: {death_event_id}")

                if death_event_id:
                    # Update existing death event
                    if 'death_date' in person_data and person_data['death_date']:
                        events[death_event_id]['date'] = person_data['death_date']
                        print(f"  [OK] Synced death date to event {death_event_id}")

                    if 'place_of_death' in person_data and person_data['place_of_death']:
                        place_id = self.resolve_place(places, person_data['place_of_death'])
                        events[death_event_id]['place_id'] = place_id
                        print(f"  [OK] Synced death place to event {death_event_id}")

                    updated_events.append(death_event_id)
                else:
                    # Create death event if data provided
                    if person_data.get('death_date') or person_data.get('place_of_death'):
                        print(f"  -> Creating new death event...")
                        death_event_id = self.get_next_event_id(events)

                        place_id = None
                        if person_data.get('place_of_death'):
                            place_id = self.resolve_place(places, person_data['place_of_death'])

                        events[death_event_id] = {
                            'id': death_event_id,
                            'type': 'death',
                            'date': person_data.get('death_date'),
                            'place_id': place_id,
                            'content': None,
                            'description': f"Death of {person['first_name']} {person['last_name']}",
                            'title': None,
                            'source': None,
                            'notes': 'Auto-generated from person update',
                            'tags': [],
                            'links': []
                        }

                        # Add person as deceased
                        ep_id = self.get_next_event_participation_id(event_participations)
                        event_participations[ep_id] = {
                            'id': ep_id,
                            'event_id': death_event_id,
                            'person_id': person_id,
                            'role': 'deceased'
                        }

                        updated_events.append(death_event_id)
                        print(f"  [OK] Created death event: {death_event_id} with participation {ep_id}")

            # Update data structure
            data['places'] = places

            self.save_data(data)

            print(f"[OK] Updated person: {person_id}")
            if updated_events:
                print(f"  Synced to {len(updated_events)} event(s): {', '.join(updated_events)}")

            return {
                'success': True,
                'person': person,
                'updated_events': updated_events,
                'message': f'Successfully updated person {person_id}'
            }

        except Exception as e:
            print(f"[ERR] Error updating person: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def delete_person(self, request_data):
        """Delete a person and all their event participations and relationships"""
        try:
            data = self.load_data()

            persons = data['persons']
            events = data['events']
            event_participations = data.get('event_participations', {})
            family_relationships = data.get('family_relationships', {})

            person_id = request_data.get('person_id')
            if not person_id or person_id not in persons:
                return {'success': False, 'error': 'Person not found'}

            # Delete the person
            deleted_person = persons.pop(person_id)

            # Delete all event participations for this person
            eps_to_delete = [ep_id for ep_id, ep in event_participations.items()
                           if ep['person_id'] == person_id]

            events_to_check = set()
            for ep_id in eps_to_delete:
                events_to_check.add(event_participations[ep_id]['event_id'])
                del event_participations[ep_id]

            # Delete all family relationships involving this person
            rels_to_delete = [rel_id for rel_id, rel in family_relationships.items()
                            if rel['person_1_id'] == person_id or rel['person_2_id'] == person_id]

            for rel_id in rels_to_delete:
                del family_relationships[rel_id]

            # Check for and delete empty events. events_to_check is a set, whose
            # iteration order depends on Python's per-process string hash
            # randomization - sorted() keeps events_deleted deterministic.
            events_deleted = []
            for event_id in sorted(events_to_check):
                # Count remaining participants
                remaining_participants = sum(1 for ep in event_participations.values()
                                           if ep['event_id'] == event_id)
                if remaining_participants == 0:
                    events.pop(event_id, None)
                    events_deleted.append(event_id)

            self.save_data(data)

            print(f"[OK] Deleted person: {person_id}")
            print(f"  Removed {len(eps_to_delete)} event participations")
            print(f"  Removed {len(rels_to_delete)} family relationships")
            if events_deleted:
                print(f"  Deleted {len(events_deleted)} empty events: {', '.join(events_deleted)}")

            return {
                'success': True,
                'person_id': person_id,
                'deleted_participations': len(eps_to_delete),
                'deleted_relationships': len(rels_to_delete),
                'deleted_events': events_deleted,
                'message': f'Successfully deleted person {person_id}'
            }

        except Exception as e:
            print(f"[ERR] Error deleting person: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def delete_event(self, request_data):
        """Delete an event and all its participations"""
        try:
            data = self.load_data()

            events = data['events']
            event_participations = data.get('event_participations', {})

            event_id = request_data.get('event_id')
            if not event_id or event_id not in events:
                return {'success': False, 'error': 'Event not found'}

            # Delete the event
            deleted_event = events.pop(event_id)

            # Delete all event participations for this event
            eps_to_delete = [ep_id for ep_id, ep in event_participations.items()
                           if ep['event_id'] == event_id]

            for ep_id in eps_to_delete:
                del event_participations[ep_id]

            self.save_data(data)

            print(f"[OK] Deleted event: {event_id}")
            print(f"  Removed {len(eps_to_delete)} event participations")

            return {
                'success': True,
                'event_id': event_id,
                'deleted_participations': len(eps_to_delete),
                'message': f'Successfully deleted event {event_id}'
            }

        except Exception as e:
            print(f"[ERR] Error deleting event: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def add_relationship(self, rel_data):
        """Add a new EVENT-BASED relationship between two persons (Step 10)"""
        try:
            data = self.load_data()

            persons = data['persons']
            events = data['events']
            event_participations = data.get('event_participations', {})

            base_person_id = rel_data['base_person_id']
            target_person_id = rel_data['target_person_id']
            rel_type = rel_data['relationship_type']
            role = rel_data['role']

            # Validate persons exist
            if base_person_id not in persons:
                return {'success': False, 'error': f'Base person {base_person_id} not found'}
            if target_person_id not in persons:
                return {'success': False, 'error': f'Target person {target_person_id} not found'}

            base_person = persons[base_person_id]
            target_person = persons[target_person_id]

            created_event = None
            updated_event = None

            # Step 10: Handle relationship types by creating/updating events
            if rel_type == 'parent':
                # Adding parent to base person: find/create birth event for base, add target as parent
                child_id = base_person_id
                parent_id = target_person_id
                parent_role = role  # 'father' or 'mother'

                # Find existing birth event for child
                birth_event_id = self.find_birth_event_for_person(events, event_participations, child_id)

                if birth_event_id:
                    # Update existing birth event
                    updated_event = birth_event_id
                    print(f"  Found existing birth event: {birth_event_id}")
                else:
                    # Create new birth event
                    birth_event_id = self.get_next_event_id(events)
                    child = persons[child_id]
                    events[birth_event_id] = {
                        'id': birth_event_id,
                        'type': 'birth',
                        'date': None,
                        'place_id': None,
                        'content': None,
                        'description': f"Birth of {child['first_name']} {child['last_name']}",
                        'title': None,
                        'source': None,
                        'notes': 'Auto-generated from relationship addition',
                        'tags': [],
                        'links': []
                    }
                    # Add child as participant
                    ep_id = self.get_next_event_participation_id(event_participations)
                    event_participations[ep_id] = {
                        'id': ep_id,
                        'event_id': birth_event_id,
                        'person_id': child_id,
                        'role': 'child'
                    }
                    created_event = birth_event_id
                    print(f"  [OK] Created birth event: {birth_event_id}")

                # Add parent as participant
                ep_id = self.get_next_event_participation_id(event_participations)
                event_participations[ep_id] = {
                    'id': ep_id,
                    'event_id': birth_event_id,
                    'person_id': parent_id,
                    'role': parent_role
                }
                print(f"  [OK] Added {parent_role} to birth event")

                # Step 13: Check if both parents are now in birth event, create marriage if needed
                self.create_parent_marriage_if_needed(events, event_participations, birth_event_id, persons)

            elif rel_type == 'child':
                # Adding child to base person: find/create birth event for target, add base as parent
                child_id = target_person_id
                parent_id = base_person_id
                parent_role = self.determine_parent_role(base_person)

                # Find existing birth event for child
                birth_event_id = self.find_birth_event_for_person(events, event_participations, child_id)

                if birth_event_id:
                    updated_event = birth_event_id
                    print(f"  Found existing birth event: {birth_event_id}")
                else:
                    # Create new birth event
                    birth_event_id = self.get_next_event_id(events)
                    child = persons[child_id]
                    events[birth_event_id] = {
                        'id': birth_event_id,
                        'type': 'birth',
                        'date': None,
                        'place_id': None,
                        'content': None,
                        'description': f"Birth of {child['first_name']} {child['last_name']}",
                        'title': None,
                        'source': None,
                        'notes': 'Auto-generated from relationship addition',
                        'tags': [],
                        'links': []
                    }
                    # Add child as participant
                    ep_id = self.get_next_event_participation_id(event_participations)
                    event_participations[ep_id] = {
                        'id': ep_id,
                        'event_id': birth_event_id,
                        'person_id': child_id,
                        'role': 'child'
                    }
                    created_event = birth_event_id
                    print(f"  [OK] Created birth event: {birth_event_id}")

                # Add parent as participant
                ep_id = self.get_next_event_participation_id(event_participations)
                event_participations[ep_id] = {
                    'id': ep_id,
                    'event_id': birth_event_id,
                    'person_id': parent_id,
                    'role': parent_role
                }
                print(f"  [OK] Added {parent_role} to birth event")

                # Step 13: Check if both parents are now in birth event, create marriage if needed
                self.create_parent_marriage_if_needed(events, event_participations, birth_event_id, persons)

            elif rel_type == 'spouse':
                # Adding spouse: find/create marriage event
                person1_id = base_person_id
                person2_id = target_person_id

                # Find existing marriage event between these two
                marriage_event_id = self.find_marriage_event_between(events, event_participations, person1_id, person2_id)

                if marriage_event_id:
                    updated_event = marriage_event_id
                    print(f"  Found existing marriage event: {marriage_event_id}")
                else:
                    # Create new marriage event
                    marriage_event_id = self.get_next_event_id(events)
                    person1 = persons[person1_id]
                    person2 = persons[person2_id]
                    events[marriage_event_id] = {
                        'id': marriage_event_id,
                        'type': 'marriage',
                        'date': None,
                        'place_id': None,
                        'content': None,
                        'description': f"Marriage of {person1['first_name']} {person1['last_name']} and {person2['first_name']} {person2['last_name']}",
                        'title': None,
                        'source': None,
                        'notes': 'Auto-generated from relationship addition',
                        'tags': [],
                        'links': []
                    }

                    # Add both as participants
                    for person_id, person in [(person1_id, person1), (person2_id, person2)]:
                        ep_id = self.get_next_event_participation_id(event_participations)
                        participant_role = 'groom' if person.get('gender') == 'M' else 'bride'
                        event_participations[ep_id] = {
                            'id': ep_id,
                            'event_id': marriage_event_id,
                            'person_id': person_id,
                            'role': participant_role
                        }

                    created_event = marriage_event_id
                    print(f"  [OK] Created marriage event: {marriage_event_id}")

            elif rel_type == 'godparent':
                # Godparent: find/create birth/baptism event for base, add target as godparent
                child_id = base_person_id
                godparent_id = target_person_id

                # Find existing birth event for child
                birth_event_id = self.find_birth_event_for_person(events, event_participations, child_id)

                if birth_event_id:
                    updated_event = birth_event_id
                    print(f"  Found existing birth event: {birth_event_id}")
                else:
                    # Create new birth event
                    birth_event_id = self.get_next_event_id(events)
                    child = persons[child_id]
                    events[birth_event_id] = {
                        'id': birth_event_id,
                        'type': 'birth',
                        'date': None,
                        'place_id': None,
                        'content': None,
                        'description': f"Birth of {child['first_name']} {child['last_name']}",
                        'title': None,
                        'source': None,
                        'notes': 'Auto-generated from relationship addition',
                        'tags': [],
                        'links': []
                    }
                    # Add child as participant
                    ep_id = self.get_next_event_participation_id(event_participations)
                    event_participations[ep_id] = {
                        'id': ep_id,
                        'event_id': birth_event_id,
                        'person_id': child_id,
                        'role': 'child'
                    }
                    created_event = birth_event_id
                    print(f"  [OK] Created birth event: {birth_event_id}")

                # Add godparent as participant
                ep_id = self.get_next_event_participation_id(event_participations)
                event_participations[ep_id] = {
                    'id': ep_id,
                    'event_id': birth_event_id,
                    'person_id': godparent_id,
                    'role': 'godparent'
                }
                print(f"  [OK] Added godparent to birth event")

            else:
                return {'success': False, 'error': f'Unknown relationship type: {rel_type}'}

            self.save_data(data)

            print(f"[OK] Added event-based relationship: {rel_type} between {base_person_id} and {target_person_id}")

            return {
                'success': True,
                'created_event': created_event,
                'updated_event': updated_event,
                'message': f'Successfully added {rel_type} relationship'
            }

        except Exception as e:
            print(f"[ERR] Error adding relationship: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def add_event(self, event_data):
        """Add a new event with participants"""
        try:
            data = self.load_data()

            persons = data['persons']
            places = data.get('places', {})
            events = data['events']
            event_participations = data.get('event_participations', {})

            # Generate event ID
            max_event_id = max([int(e['id'][1:]) for e in events.values()], default=0)
            event_id = f"E{(max_event_id + 1):04d}"

            # Handle place
            place_id = self.handle_place(places, event_data)

            # Create event. Canonical field set/order
            # (normalize_data_schema.py) - this literal was previously
            # missing 'description'/'source' entirely (see
            # JAVA_MIGRATION.md's Phase 0 addendum on add_event's event
            # shape) and stored event_data['date'] unnormalized (missing
            # 'circa' - see the date-shape addendum). Both closed here
            # while porting step 3.
            new_event = {
                'id': event_id,
                'type': event_data['type'],
                'date': self.normalize_date(event_data['date']),
                'place_id': place_id,
                'content': '',  # Will be generated from participants
                'description': None,
                'title': event_data.get('title', None),
                'source': None,
                'notes': event_data.get('notes', ''),
                'tags': event_data.get('tags', []),
                'links': event_data.get('links', [])
            }

            events[event_id] = new_event

            # Process participants
            max_ep_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0) if event_participations else 0

            content_parts = []
            new_persons = []  # Track newly created persons

            for participant in event_data.get('participants', []):
                person_id = participant.get('existing_person_id')
                is_existing_person = bool(person_id)

                # Create new person if needed
                if not person_id and participant.get('first_name') and participant.get('last_name'):
                    max_person_id = max([int(p['id'][1:]) for p in persons.values()], default=0)
                    person_id = f"P{(max_person_id + 1):04d}"

                    # Calculate birth_date from age if provided
                    birth_date = None
                    if participant.get('calculated_birth_year'):
                        birth_date = {
                            'year': participant['calculated_birth_year'],
                            'month': None,
                            'day': None,
                            'circa': True
                        }

                    # Step 52: Infer gender from role if not explicitly provided
                    role_gender_map = {'groom': 'M', 'bride': 'F', 'father': 'M', 'mother': 'F'}
                    inferred_gender = participant.get('gender') or role_gender_map.get(participant.get('role'), 'U')

                    # Canonical field set/order (normalize_data_schema.py) -
                    # this literal (and parent_person below) was previously
                    # missing 'tags'/'notes' entirely (see JAVA_MIGRATION.md's
                    # Phase 0 addendum on add_event's person literals).
                    new_person = {
                        'id': person_id,
                        'first_name': participant['first_name'],
                        'last_name': participant['last_name'],
                        'gender': inferred_gender,
                        'maiden_name': participant.get('maiden_name'),
                        'occupation': participant.get('occupation'),
                        'tags': [],
                        'notes': None
                    }

                    persons[person_id] = new_person
                    new_persons.append(new_person)  # Track new person

                    # Handle parents if provided - create persons and establish relationships
                    created_parents = {'mother': None, 'father': None}

                    for parent_type in ['mother', 'father']:
                        parent_data = participant.get(f'parent_{parent_type}')
                        if parent_data and parent_data.get('first_name') and parent_data.get('last_name'):
                            # Check if using existing person
                            parent_id = parent_data.get('existing_person_id')

                            if not parent_id:
                                # Create new parent person
                                max_person_id = max([int(p['id'][1:]) for p in persons.values()], default=0)
                                parent_id = f"P{(max_person_id + 1):04d}"

                                parent_person = {
                                    'id': parent_id,
                                    'first_name': parent_data['first_name'],
                                    'last_name': parent_data['last_name'],
                                    'gender': 'F' if parent_type == 'mother' else 'M',
                                    'maiden_name': parent_data.get('maiden_name'),
                                    'occupation': None,
                                    'tags': [],
                                    'notes': None
                                }

                                persons[parent_id] = parent_person
                                new_persons.append(parent_person)
                                print(f"  [OK] Created parent: {parent_id} - {parent_person['first_name']} {parent_person['last_name']}")

                            created_parents[parent_type] = parent_id

                    # Create a birth event for new persons, unless:
                    # - role is 'child' in a birth event (the main event IS already the birth event)
                    # - a birth event already exists for this person (update it instead)
                    participant_role = participant.get('role')
                    is_child_in_birth_event = (participant_role == 'child' and event_data.get('type') == 'birth')
                    existing_birth_event_id = self.find_birth_event_for_person(events, event_participations, person_id)

                    if is_child_in_birth_event:
                        # The main event is this person's birth event — no separate auto-birth-event needed,
                        # but any new parents still need to be linked to THIS event as father/mother.
                        print(f"  [SKIP] Auto-birth-event for {person_id}: main event {event_id} is the birth event")
                        for parent_type, par_id in created_parents.items():
                            if par_id:
                                already_participant = any(
                                    ep['event_id'] == event_id and ep['person_id'] == par_id
                                    for ep in event_participations.values()
                                )
                                if not already_participant:
                                    max_ep_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)
                                    max_ep_id += 1
                                    ep_id = f"EP{max_ep_id:04d}"
                                    event_participations[ep_id] = {
                                        'id': ep_id,
                                        'event_id': event_id,
                                        'person_id': par_id,
                                        'role': parent_type
                                    }
                                    print(f"  [OK] Added {parent_type} to birth event {event_id} (main event)")
                    elif existing_birth_event_id:
                        # Birth event already exists — add any new parents to it instead of creating a duplicate
                        print(f"  [SKIP] Birth event {existing_birth_event_id} already exists for {person_id}, updating parents")
                        for parent_type, par_id in created_parents.items():
                            if par_id:
                                already_participant = any(
                                    ep['event_id'] == existing_birth_event_id and ep['person_id'] == par_id
                                    for ep in event_participations.values()
                                )
                                if not already_participant:
                                    max_ep_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)
                                    max_ep_id += 1
                                    ep_id = f"EP{max_ep_id:04d}"
                                    event_participations[ep_id] = {
                                        'id': ep_id,
                                        'event_id': existing_birth_event_id,
                                        'person_id': par_id,
                                        'role': parent_type
                                    }
                                    print(f"  [OK] Added {parent_type} to existing birth event {existing_birth_event_id}")
                    else:
                        # Create new auto-birth-event for this new person
                        max_event_id = max([int(e['id'][1:]) for e in events.values()], default=0)
                        birth_event_id = f"E{(max_event_id + 1):04d}"

                        birth_event = {
                            'id': birth_event_id,
                            'type': 'birth',
                            'date': birth_date,
                            'place_id': None,
                            'content': '',
                            'description': f"Birth of {new_person['first_name']} {new_person['last_name']}",
                            'title': None,
                            'source': None,
                            'notes': 'Auto-generated from event participation',
                            'tags': [],
                            'links': []
                        }
                        events[birth_event_id] = birth_event

                        # Add child as participant
                        max_ep_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)
                        max_ep_id += 1
                        ep_id = f"EP{max_ep_id:04d}"
                        event_participations[ep_id] = {
                            'id': ep_id,
                            'event_id': birth_event_id,
                            'person_id': person_id,
                            'role': 'child'
                        }

                        # Add parents as participants
                        for parent_type, par_id in created_parents.items():
                            if par_id:
                                max_ep_id += 1
                                ep_id = f"EP{max_ep_id:04d}"
                                event_participations[ep_id] = {
                                    'id': ep_id,
                                    'event_id': birth_event_id,
                                    'person_id': par_id,
                                    'role': parent_type
                                }

                        print(f"  [OK] Created birth event: {birth_event_id} for {person_id} (date: {birth_date})")

                    # Create marriage event between parents if both exist
                    if created_parents['mother'] and created_parents['father']:
                        max_event_id = max([int(e['id'][1:]) for e in events.values()], default=0)
                        marriage_event_id = f"E{(max_event_id + 1):04d}"

                        mother = persons[created_parents['mother']]
                        father = persons[created_parents['father']]

                        marriage_event = {
                            'id': marriage_event_id,
                            'type': 'marriage',
                            'date': None,
                            'place_id': None,
                            'content': '',
                            'description': f"Marriage of {father['first_name']} {father['last_name']} and {mother['first_name']} {mother['last_name']}",
                            'title': None,
                            'source': None,
                            'notes': 'Auto-generated from child birth event',
                            'tags': [],
                            'links': []
                        }
                        events[marriage_event_id] = marriage_event

                        # Add parents as bride and groom
                        max_ep_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)
                        max_ep_id += 1
                        ep_id = f"EP{max_ep_id:04d}"
                        event_participations[ep_id] = {
                            'id': ep_id,
                            'event_id': marriage_event_id,
                            'person_id': created_parents['father'],
                            'role': 'groom'
                        }

                        max_ep_id += 1
                        ep_id = f"EP{max_ep_id:04d}"
                        event_participations[ep_id] = {
                            'id': ep_id,
                            'event_id': marriage_event_id,
                            'person_id': created_parents['mother'],
                            'role': 'bride'
                        }

                        print(f"  [OK] Created marriage event: {marriage_event_id} between parents")

                # Update name fields for existing persons if changed in the form
                if is_existing_person and person_id and person_id in persons:
                    last_name = participant.get('last_name', '').strip()
                    maiden_name = participant.get('maiden_name', '').strip()
                    if last_name and last_name != persons[person_id].get('last_name'):
                        persons[person_id]['last_name'] = last_name
                        print(f"  [OK] Updated last_name for existing person {person_id}: {last_name}")
                    if maiden_name and maiden_name != persons[person_id].get('maiden_name'):
                        persons[person_id]['maiden_name'] = maiden_name
                        print(f"  [OK] Updated maiden_name for existing person {person_id}: {maiden_name}")

                if person_id:
                    # Create event participation (recalculate max to stay correct regardless of which branch above ran)
                    max_ep_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)
                    max_ep_id += 1
                    ep_id = f"EP{max_ep_id:04d}"

                    event_participations[ep_id] = {
                        'id': ep_id,
                        'event_id': event_id,
                        'person_id': person_id,
                        'role': participant['role']
                    }

                    # Add to content
                    person = persons[person_id]
                    person_name = f"{person['first_name']} {person['last_name']}"
                    if participant.get('age'):
                        person_name += f" ({participant['age']})"
                    content_parts.append(f"{participant['role']}: {person_name}")

            # Generate content (use provided content or auto-generate from participants)
            if event_data.get('content'):
                new_event['content'] = event_data['content']
            else:
                new_event['content'] = ', '.join(content_parts) if content_parts else 'Event created'

            # Sync parents to birth events
            self.sync_parents_to_birth_events(event_data, persons, events, event_participations, places)

            # Step 21: Sync ages to birth years
            self.sync_ages_to_birth_years(event_id, event_data, persons, events, event_participations)

            # Save data
            # Step 30: Auto-create marriage between parents if this is a birth event
            if new_event['type'] == 'birth':
                self.create_parent_marriage_if_needed(events, event_participations, event_id, persons)

            data['places'] = places
            data['events'] = events
            data['event_participations'] = event_participations
            data['persons'] = persons

            self.save_data(data)

            print(f"[OK] Added event: {event_id} - {new_event['type']} with {len(content_parts)} participants")
            if new_persons:
                print(f"  Created {len(new_persons)} new person(s)")

            return {
                'success': True,
                'event': new_event,
                'new_persons': new_persons,
                'message': f'Successfully added event {event_id}'
            }

        except Exception as e:
            print(f"[ERR] Error adding event: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def update_event(self, event_data):
        """Update an existing event"""
        try:
            data = self.load_data()

            event_id = event_data['event_id']
            events = data['events']

            if event_id not in events:
                return {'success': False, 'error': f'Event {event_id} not found'}

            places = data.get('places', {})
            event_participations = data.get('event_participations', {})
            persons = data['persons']

            # Update event basic info
            event = events[event_id]
            event['type'] = event_data['type']
            event['title'] = event_data.get('title', None)
            event['date'] = self.normalize_date(event_data['date'])
            event['tags'] = event_data.get('tags', [])
            event['links'] = event_data.get('links', [])
            event['notes'] = event_data.get('notes', '')

            place_id = self.handle_place(places, event_data)

            event['place_id'] = place_id

            # Remove old participations
            old_participations = {ep_id: ep for ep_id, ep in event_participations.items() if ep['event_id'] == event_id}
            for ep_id in old_participations.keys():
                del event_participations[ep_id]

            # Add new participations (similar to add_event)
            max_ep_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0) if event_participations else 0
            content_parts = []
            new_persons = []  # Track newly created persons

            for participant in event_data.get('participants', []):
                person_id = participant.get('existing_person_id')
                is_existing_person = bool(person_id)

                # Create new person if needed (same logic as add_event)
                if not person_id and participant.get('first_name') and participant.get('last_name'):
                    max_person_id = max([int(p['id'][1:]) for p in persons.values()], default=0)
                    person_id = f"P{(max_person_id + 1):04d}"

                    birth_date = None
                    if participant.get('calculated_birth_year'):
                        birth_date = {
                            'year': participant['calculated_birth_year'],
                            'month': None,
                            'day': None,
                            'circa': True
                        }

                    # Step 52: Infer gender from role if not explicitly provided
                    role_gender_map = {'groom': 'M', 'bride': 'F', 'father': 'M', 'mother': 'F'}
                    inferred_gender = participant.get('gender') or role_gender_map.get(participant.get('role'), 'U')

                    new_person = {
                        'id': person_id,
                        'first_name': participant['first_name'],
                        'last_name': participant['last_name'],
                        'maiden_name': participant.get('maiden_name'),
                        'gender': inferred_gender,
                        'occupation': participant.get('occupation'),
                        'tags': [],
                        'notes': None
                    }

                    persons[person_id] = new_person
                    new_persons.append(new_person)  # Track new person

                    # Handle parents if provided - create persons and establish relationships
                    created_parents = {'mother': None, 'father': None}

                    for parent_type in ['mother', 'father']:
                        parent_data = participant.get(f'parent_{parent_type}')
                        if parent_data and parent_data.get('first_name') and parent_data.get('last_name'):
                            # Check if using existing person
                            parent_id = parent_data.get('existing_person_id')

                            if not parent_id:
                                # Create new parent person
                                max_person_id = max([int(p['id'][1:]) for p in persons.values()], default=0)
                                parent_id = f"P{(max_person_id + 1):04d}"

                                parent_person = {
                                    'id': parent_id,
                                    'first_name': parent_data['first_name'],
                                    'last_name': parent_data['last_name'],
                                    'maiden_name': parent_data.get('maiden_name'),
                                    'gender': 'F' if parent_type == 'mother' else 'M',
                                    'occupation': None,
                                    'tags': [],
                                    'notes': None
                                }

                                persons[parent_id] = parent_person
                                new_persons.append(parent_person)
                                print(f"  [OK] Created parent: {parent_id} - {parent_person['first_name']} {parent_person['last_name']}")

                            created_parents[parent_type] = parent_id

                    # Create a birth event for this new person, unless:
                    # - role is 'child' in a birth event (the event being
                    #   updated IS already their birth event)
                    # - a birth event already exists for this person (update
                    #   it instead of creating a duplicate)
                    # Mirrors add_event's equivalent branch.
                    participant_role = participant.get('role')
                    is_child_in_birth_event = (participant_role == 'child' and event_data.get('type') == 'birth')
                    existing_birth_event_id = self.find_birth_event_for_person(events, event_participations, person_id)

                    if is_child_in_birth_event:
                        # The main event is this person's birth event — no separate auto-birth-event needed,
                        # but any new parents still need to be linked to THIS event as father/mother.
                        print(f"  [SKIP] Auto-birth-event for {person_id}: main event {event_id} is the birth event")
                        for parent_type, par_id in created_parents.items():
                            if par_id:
                                already_participant = any(
                                    ep['event_id'] == event_id and ep['person_id'] == par_id
                                    for ep in event_participations.values()
                                )
                                if not already_participant:
                                    max_ep_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)
                                    max_ep_id += 1
                                    ep_id = f"EP{max_ep_id:04d}"
                                    event_participations[ep_id] = {
                                        'id': ep_id,
                                        'event_id': event_id,
                                        'person_id': par_id,
                                        'role': parent_type
                                    }
                                    print(f"  [OK] Added {parent_type} to birth event {event_id} (main event)")
                    elif existing_birth_event_id:
                        print(f"  [SKIP] Birth event {existing_birth_event_id} already exists for {person_id}, updating parents")
                        for parent_type, par_id in created_parents.items():
                            if par_id:
                                already_participant = any(
                                    ep['event_id'] == existing_birth_event_id and ep['person_id'] == par_id
                                    for ep in event_participations.values()
                                )
                                if not already_participant:
                                    max_ep_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)
                                    max_ep_id += 1
                                    ep_id = f"EP{max_ep_id:04d}"
                                    event_participations[ep_id] = {
                                        'id': ep_id,
                                        'event_id': existing_birth_event_id,
                                        'person_id': par_id,
                                        'role': parent_type
                                    }
                                    print(f"  [OK] Added {parent_type} to existing birth event {existing_birth_event_id}")
                    else:
                        max_event_id = max([int(e['id'][1:]) for e in events.values()], default=0)
                        birth_event_id = f"E{(max_event_id + 1):04d}"

                        birth_event = {
                            'id': birth_event_id,
                            'type': 'birth',
                            'date': birth_date,
                            'place_id': None,
                            'content': '',
                            'description': f"Birth of {new_person['first_name']} {new_person['last_name']}",
                            'title': None,
                            'source': None,
                            'notes': 'Auto-generated from event participation',
                            'tags': [],
                            'links': []
                        }
                        events[birth_event_id] = birth_event

                        # Add child as participant — use outer max_ep_id to avoid ID collision
                        max_ep_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)
                        max_ep_id += 1
                        ep_id = f"EP{max_ep_id:04d}"
                        event_participations[ep_id] = {
                            'id': ep_id,
                            'event_id': birth_event_id,
                            'person_id': person_id,
                            'role': 'child'
                        }

                        # Add parents as participants
                        for parent_type, parent_id_temp in created_parents.items():
                            if parent_id_temp:
                                max_ep_id += 1
                                ep_id = f"EP{max_ep_id:04d}"
                                event_participations[ep_id] = {
                                    'id': ep_id,
                                    'event_id': birth_event_id,
                                    'person_id': parent_id_temp,
                                    'role': parent_type
                                }

                        print(f"  [OK] Created birth event: {birth_event_id} for {person_id} (date: {birth_date})")

                    # Create marriage event between parents if both exist
                    if created_parents['mother'] and created_parents['father']:
                        max_event_id = max([int(e['id'][1:]) for e in events.values()], default=0)
                        marriage_event_id = f"E{(max_event_id + 1):04d}"

                        mother = persons[created_parents['mother']]
                        father = persons[created_parents['father']]

                        marriage_event = {
                            'id': marriage_event_id,
                            'type': 'marriage',
                            'date': None,
                            'place_id': None,
                            'content': '',
                            'description': f"Marriage of {father['first_name']} {father['last_name']} and {mother['first_name']} {mother['last_name']}",
                            'title': None,
                            'source': None,
                            'notes': 'Auto-generated from child birth event',
                            'tags': [],
                            'links': []
                        }
                        events[marriage_event_id] = marriage_event

                        # Add parents as bride and groom
                        max_ep_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)
                        max_ep_id += 1
                        ep_id = f"EP{max_ep_id:04d}"
                        event_participations[ep_id] = {
                            'id': ep_id,
                            'event_id': marriage_event_id,
                            'person_id': created_parents['father'],
                            'role': 'groom'
                        }

                        max_ep_id += 1
                        ep_id = f"EP{max_ep_id:04d}"
                        event_participations[ep_id] = {
                            'id': ep_id,
                            'event_id': marriage_event_id,
                            'person_id': created_parents['mother'],
                            'role': 'bride'
                        }

                        print(f"  [OK] Created marriage event: {marriage_event_id} between parents")

                # Update name fields for existing persons if changed in the form
                if is_existing_person and person_id and person_id in persons:
                    last_name = participant.get('last_name', '').strip()
                    maiden_name = participant.get('maiden_name', '').strip()
                    if last_name and last_name != persons[person_id].get('last_name'):
                        persons[person_id]['last_name'] = last_name
                        print(f"  [OK] Updated last_name for existing person {person_id}: {last_name}")
                    if maiden_name and maiden_name != persons[person_id].get('maiden_name'):
                        persons[person_id]['maiden_name'] = maiden_name
                        print(f"  [OK] Updated maiden_name for existing person {person_id}: {maiden_name}")

                if person_id:
                    max_ep_id += 1
                    ep_id = f"EP{max_ep_id:04d}"

                    event_participations[ep_id] = {
                        'id': ep_id,
                        'event_id': event_id,
                        'person_id': person_id,
                        'role': participant['role']
                    }

                    person = persons[person_id]
                    person_name = f"{person['first_name']} {person['last_name']}"
                    if participant.get('age'):
                        person_name += f" ({participant['age']})"
                    content_parts.append(f"{participant['role']}: {person_name}")

            # Update content (use provided content or auto-generate from participants)
            if event_data.get('content'):
                event['content'] = event_data['content']
            else:
                event['content'] = ', '.join(content_parts) if content_parts else 'Event updated'

            # Sync parents to birth events
            self.sync_parents_to_birth_events(event_data, persons, data['events'], event_participations, places)

            # Step 21: Sync ages to birth years
            self.sync_ages_to_birth_years(event_id, event_data, persons, events, event_participations)

            # Step 30: Auto-create marriage between parents if this is a birth event
            if event_data['type'] == 'birth':
                self.create_parent_marriage_if_needed(events, event_participations, event_id, persons)

            # Collect all persons that were modified (existing persons with updated maiden_name)
            modified_persons = []
            for participant in event_data.get('participants', []):
                pid = participant.get('existing_person_id')
                if pid and pid in persons and participant.get('maiden_name'):
                    modified_persons.append(persons[pid])

            # Ensure persons changes are reflected in data before saving
            data['persons'] = persons

            self.save_data(data)

            print(f"[OK] Updated event {event_id}")

            if new_persons:
                print(f"  Created {len(new_persons)} new person(s)")
            if modified_persons:
                print(f"  Modified {len(modified_persons)} existing person(s)")

            # Return current participations for this event so client can patch in-memory
            updated_participations = {
                ep_id: ep for ep_id, ep in event_participations.items()
                if ep['event_id'] == event_id
            }

            return {
                'success': True,
                'event': event,
                'event_participations': updated_participations,
                'new_persons': new_persons,
                'modified_persons': modified_persons,
                'message': f'Successfully updated event {event_id}'
            }

        except Exception as e:
            print(f"[ERR] Error updating event: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def sync_parents_to_birth_events(self, event_data, persons, events, event_participations, places):
        """
        Sync parent information from event participants to their birth events.
        When parents are added to groom/bride/deceased/etc., ensure they're in that person's birth event.
        """
        try:
            # Map participant roles to their parent roles
            # e.g., "groom_parent_father" -> main role is "groom", parent role is "father"
            parent_roles_to_sync = []

            for participant in event_data.get('participants', []):
                role = participant.get('role', '')
                person_id = participant.get('existing_person_id')

                # Check if this is a parent role (e.g., groom_parent_father, bride_parent_mother)
                if '_parent_' in role:
                    parts = role.split('_parent_')
                    if len(parts) == 2:
                        main_role = parts[0]  # e.g., "groom"
                        parent_type = parts[1]  # e.g., "father" or "mother"

                        # Find the main person (groom, bride, deceased, etc.)
                        main_person_id = None
                        for p in event_data.get('participants', []):
                            if p.get('role') == main_role:
                                main_person_id = p.get('existing_person_id')
                                break

                        if main_person_id and person_id:
                            parent_roles_to_sync.append({
                                'child_id': main_person_id,
                                'parent_id': person_id,
                                'parent_role': parent_type  # 'father' or 'mother'
                            })

            # Process each parent-child relationship
            for sync_info in parent_roles_to_sync:
                child_id = sync_info['child_id']
                parent_id = sync_info['parent_id']
                parent_role = sync_info['parent_role']

                # Find or create birth event for the child
                birth_event_id = self.find_birth_event_for_person(events, event_participations, child_id)

                if not birth_event_id:
                    # Create birth event for this person
                    max_event_id = max([int(e['id'][1:]) for e in events.values()], default=0)
                    birth_event_id = f"E{(max_event_id + 1):04d}"

                    child = persons.get(child_id)
                    if not child:
                        continue

                    birth_event = {
                        'id': birth_event_id,
                        'type': 'birth',
                        'date': None,
                        'place_id': None,
                        'content': '',
                        'description': f"Birth of {child.get('first_name', '')} {child.get('last_name', '')}",
                        'title': None,
                        'source': None,
                        'notes': 'Auto-generated for parent synchronization',
                        'tags': [],
                        'links': []
                    }
                    events[birth_event_id] = birth_event

                    # Add child as participant
                    max_ep_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)
                    ep_id = f"EP{(max_ep_id + 1):04d}"
                    event_participations[ep_id] = {
                        'id': ep_id,
                        'event_id': birth_event_id,
                        'person_id': child_id,
                        'role': 'child'
                    }

                    print(f"  [OK] Created birth event {birth_event_id} for {child_id}")

                # Check if parent already exists in birth event
                parent_exists = False
                for ep in event_participations.values():
                    if (ep['event_id'] == birth_event_id and
                        ep['role'] == parent_role and
                        ep['person_id'] == parent_id):
                        parent_exists = True
                        break

                if not parent_exists:
                    # Check if there's already a different person in this parent role
                    existing_parent = None
                    for ep in event_participations.values():
                        if ep['event_id'] == birth_event_id and ep['role'] == parent_role:
                            existing_parent = ep['person_id']
                            break

                    if not existing_parent:
                        # Add parent to birth event
                        max_ep_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)
                        ep_id = f"EP{(max_ep_id + 1):04d}"
                        event_participations[ep_id] = {
                            'id': ep_id,
                            'event_id': birth_event_id,
                            'person_id': parent_id,
                            'role': parent_role
                        }

                        parent = persons.get(parent_id)
                        child = persons.get(child_id)
                        print(f"  [OK] Added {parent_role} {parent.get('first_name', '')} {parent.get('last_name', '')} to birth event of {child.get('first_name', '')} {child.get('last_name', '')}")
                    else:
                        print(f"  [WARN] {parent_role} slot already occupied in birth event {birth_event_id} for {child_id}")

        except Exception as e:
            print(f"[WARN] Warning: Error syncing parents to birth events: {str(e)}")
            # Don't fail the whole event operation if sync fails
            import traceback
            traceback.print_exc()

    def sync_ages_to_birth_years(self, event_id, event_data, persons, events, event_participations):
        """
        Step 21: When age is provided for participants, calculate and update their birth year.
        Formula: birth_year = event_year - age
        """
        try:
            event_date = event_data.get('date')
            if not event_date or not event_date.get('year'):
                return

            event_year = event_date['year']

            # Process all participants in this event
            for participant in event_data.get('participants', []):
                age = participant.get('age')
                person_id = participant.get('existing_person_id')

                if age and person_id and person_id in persons:
                    calculated_birth_year = event_year - age

                    # Find or create birth event for this person
                    birth_event_id = self.find_birth_event_for_person(events, event_participations, person_id)

                    if birth_event_id:
                        # Update existing birth event with age-derived year (always overwrite)
                        birth_event = events[birth_event_id]
                        birth_event['date'] = {
                            'year': calculated_birth_year,
                            'month': None,
                            'day': None,
                            'circa': True
                        }
                        print(f"  [OK] Step 21: Calculated birth year {calculated_birth_year} for {person_id} from age {age}")
                    else:
                        # Step 29: Create birth event if it doesn't exist
                        birth_event_id = self.get_next_event_id(events)
                        person = persons[person_id]

                        events[birth_event_id] = {
                            'id': birth_event_id,
                            'type': 'birth',
                            'date': {
                                'year': calculated_birth_year,
                                'month': None,
                                'day': None,
                                'circa': True
                            },
                            'place_id': None,
                            'content': '',
                            'description': f"Birth of {person.get('first_name', '')} {person.get('last_name', '')}",
                            'title': None,
                            'source': None,
                            'notes': f'Auto-generated from age {age} in event {event_id}',
                            'tags': [],
                            'links': []
                        }

                        # Add person as child
                        ep_id = self.get_next_event_participation_id(event_participations)
                        event_participations[ep_id] = {
                            'id': ep_id,
                            'event_id': birth_event_id,
                            'person_id': person_id,
                            'role': 'child'
                        }

                        print(f"  [OK] Step 29: Created birth event {birth_event_id} with year {calculated_birth_year} for {person_id} from age {age}")

        except Exception as e:
            print(f"[WARN] Warning: Error syncing ages to birth years: {str(e)}")
            import traceback
            traceback.print_exc()
