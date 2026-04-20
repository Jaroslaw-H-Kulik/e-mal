#!/usr/bin/env python3
"""
Simple HTTP server with write capability for genealogy editor.
Serves static files and handles POST requests to save merge logs.
"""

import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Ensure stdout/stderr use UTF-8 on Windows
import io
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
except AttributeError:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

print("[SERVER] Starting server (utf-8 stdout/stderr configured)")

class GenealogyServerHandler(SimpleHTTPRequestHandler):
    """Extended HTTP handler with POST support for saving data"""

    def do_GET(self):
        """Handle GET requests (serve files and API endpoints)"""
        # Handle API endpoints
        if self.path.startswith('/api/geneteka-import'):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            first_name = params.get('first_name', [''])[0]
            last_name = params.get('last_name', [''])[0]
            record_type = params.get('type', ['birth'])[0]
            response_data = self.geneteka_import(first_name, last_name, record_type)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
            return

        if self.path.startswith('/api/gedcom-person/'):
            # Extract person ID from path
            person_id = self.path.split('/')[-1]
            response_data = self.get_gedcom_person(person_id)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            return

        # Default to serving from web/ directory
        if self.path == '/':
            self.path = '/web/index.html'
        elif not self.path.startswith('/web/') and not self.path.startswith('/data/'):
            self.path = '/web' + self.path

        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        """Handle POST requests (save data)"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'

        try:
            data = json.loads(post_data.decode('utf-8'))

            # Handle different endpoints
            if self.path == '/api/save-merge-log':
                self.save_merge_log(data)
                response_data = {'status': 'success', 'message': 'Data saved successfully'}
            elif self.path == '/api/save-data':
                self.save_genealogy_data(data)
                response_data = {'status': 'success', 'message': 'Data saved successfully'}
            elif self.path == '/api/apply-enrichment':
                response_data = self.apply_enrichment(data)
            elif self.path == '/api/add-person':
                response_data = self.add_person(data)
            elif self.path == '/api/gedcom-lookup':
                response_data = self.gedcom_lookup(data)
            elif self.path == '/api/add-relationship':
                response_data = self.add_relationship(data)
            elif self.path == '/api/add-event':
                response_data = self.add_event(data)
            elif self.path == '/api/update-event':
                response_data = self.update_event(data)
            elif self.path == '/api/update-person':
                response_data = self.update_person(data)
            elif self.path == '/api/delete-person':
                response_data = self.delete_person(data)
            elif self.path == '/api/delete-event':
                response_data = self.delete_event(data)
            elif self.path == '/api/generate-parent-marriages':
                response_data = self.generate_parent_marriages()
            elif self.path == '/api/sync-all-ages-to-birth-years':
                response_data = self.sync_all_ages_to_birth_years_migration()
            elif self.path == '/api/deduplicate-witnesses-godparents':
                response_data = self.deduplicate_witnesses_godparents()
            else:
                self.send_error(404, "Endpoint not found")
                return

            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            import traceback
            log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'error.log')
            try:
                with open(log_path, 'a', encoding='utf-8') as _log:
                    _log.write(f"=== do_POST exception ===\n")
                    _log.write(f"Type: {type(e).__name__}\n")
                    _log.write(f"Repr: {repr(e)}\n")
                    traceback.print_exc(file=_log)
                    _log.write("---\n")
            except Exception as log_err:
                pass
            # Use ascii-safe message for HTTP status line (latin-1 encoding required)
            safe_msg = repr(e).encode('ascii', errors='replace').decode('ascii')
            self.send_error(500, f"Error saving data: {safe_msg}")

    def do_OPTIONS(self):
        """Handle OPTIONS requests (CORS preflight)"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def save_merge_log(self, data):
        """Save merge log to data/merge_log.json"""
        merge_log_path = 'data/merge_log.json'

        # Load existing merge log if it exists
        existing_merges = []
        if os.path.exists(merge_log_path):
            try:
                with open(merge_log_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    existing_merges = existing_data.get('merges', [])
            except:
                pass  # If file is corrupted, start fresh

        # Append new merges (avoid duplicates)
        new_merges = data.get('merges', [])
        for new_merge in new_merges:
            # Check if this merge already exists
            is_duplicate = any(
                m['kept_name'] == new_merge['kept_name'] and
                m['merged_name'] == new_merge['merged_name']
                for m in existing_merges
            )
            if not is_duplicate:
                existing_merges.append(new_merge)

        # Save updated merge log
        merge_log = {
            'instructions': 'This file contains merge records. The parser will automatically apply these merges when processing base.md.',
            'merges': existing_merges,
            'total_merges': len(existing_merges),
            'last_updated': data.get('last_updated')
        }

        with open(merge_log_path, 'w', encoding='utf-8') as f:
            json.dump(merge_log, f, ensure_ascii=False, indent=2)

        print(f"[OK] Saved merge log: {len(existing_merges)} total merges")

    def save_genealogy_data(self, data):
        """Save complete genealogy data to data/genealogy_new_model.json"""
        data_path = 'data/genealogy_new_model.json'

        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] Saved genealogy data: {len(data.get('persons', {}))} persons")

    def apply_enrichment(self, decision):
        """Apply enrichment decision and update genealogy data"""
        try:
            # Load current data
            data_path = 'data/genealogy_complete.json'
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            persons = data['persons']
            relationships = data['relationships']

            base_person_id = decision['base_person_id']
            changes = []

            # Apply personal data updates
            if decision.get('personal_data'):
                person = persons[base_person_id]
                for key, value in decision['personal_data'].items():
                    person[key] = value
                    changes.append(f"Updated {base_person_id}: {key} = {value}")

            # Apply parent decisions
            for parent_decision in decision.get('parents', []):
                if parent_decision['action'] == 'merge':
                    # Merge with existing person
                    merge_with_id = parent_decision['merge_with']
                    # Add parent relationship
                    rel_id = self.get_next_relationship_id(relationships)
                    relationships[rel_id] = {
                        'id': rel_id,
                        'type': 'biological_parent',
                        'from_person': merge_with_id,
                        'to_person': base_person_id,
                        'role': parent_decision['relationship'],
                        'evidence': ['gedcom_enrichment']
                    }
                    changes.append(f"Added parent relationship: {merge_with_id} -> {base_person_id}")

                elif parent_decision['action'] == 'create':
                    # Create new person
                    new_id = self.get_next_person_id(persons)
                    parent_data = parent_decision['data']
                    persons[new_id] = {
                        'id': new_id,
                        'given_name': parent_data['given_name'],
                        'surname': parent_data['surname'],
                        'gender': parent_data['gender'],
                        'birth_year_estimate': parent_data.get('birth_year'),
                        'death_year_estimate': parent_data.get('death_year'),
                        'confidence': 'high',
                        'data_quality': 'from_gedcom_enrichment'
                    }
                    if parent_data.get('maiden_name'):
                        persons[new_id]['maiden_name'] = parent_data['maiden_name']

                    # Add relationship
                    rel_id = self.get_next_relationship_id(relationships)
                    relationships[rel_id] = {
                        'id': rel_id,
                        'type': 'biological_parent',
                        'from_person': new_id,
                        'to_person': base_person_id,
                        'role': parent_decision['relationship'],
                        'evidence': ['gedcom_enrichment']
                    }
                    changes.append(f"Created parent {new_id}: {parent_data['given_name']} {parent_data['surname']}")

            # Apply children decisions
            for child_decision in decision.get('children', []):
                if child_decision['action'] == 'merge':
                    # Merge with existing person
                    merge_with_id = child_decision['merge_with']
                    # Add child relationship
                    rel_id = self.get_next_relationship_id(relationships)
                    relationships[rel_id] = {
                        'id': rel_id,
                        'type': 'biological_parent',
                        'from_person': base_person_id,
                        'to_person': merge_with_id,
                        'role': self.determine_parent_role(persons[base_person_id]),
                        'evidence': ['gedcom_enrichment']
                    }
                    changes.append(f"Added child relationship: {base_person_id} -> {merge_with_id}")

                elif child_decision['action'] == 'create':
                    # Create new person
                    new_id = self.get_next_person_id(persons)
                    child_data = child_decision['data']
                    persons[new_id] = {
                        'id': new_id,
                        'given_name': child_data['given_name'],
                        'surname': child_data['surname'],
                        'gender': child_data['gender'],
                        'birth_year_estimate': child_data.get('birth_year'),
                        'death_year_estimate': child_data.get('death_year'),
                        'confidence': 'high',
                        'data_quality': 'from_gedcom_enrichment'
                    }

                    # Add relationship
                    rel_id = self.get_next_relationship_id(relationships)
                    relationships[rel_id] = {
                        'id': rel_id,
                        'type': 'biological_parent',
                        'from_person': base_person_id,
                        'to_person': new_id,
                        'role': self.determine_parent_role(persons[base_person_id]),
                        'evidence': ['gedcom_enrichment']
                    }
                    changes.append(f"Created child {new_id}: {child_data['given_name']} {child_data['surname']}")

            # Save updated data
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"[OK] Applied enrichment: {len(changes)} changes")
            for change in changes:
                print(f"  - {change}")

            return {
                'success': True,
                'changes': changes,
                'persons_count': len(persons),
                'relationships_count': len(relationships)
            }

        except Exception as e:
            print(f"[ERR] Error applying enrichment: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def add_person(self, person_data):
        """Add a new person to the genealogy data with auto-created events (Step 9)"""
        try:
            # Load current data (NEW MODEL)
            data_path = 'data/genealogy_new_model.json'
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            persons = data['persons']
            places = data.get('places', {})
            events = data['events']
            event_participations = data.get('event_participations', {})

            # Generate new person ID
            new_id = self.get_next_person_id(persons)

            # Create person object with NEW model fields
            new_person = {
                'id': new_id,
                'first_name': person_data.get('given_name', person_data.get('first_name', '')),
                'last_name': person_data.get('surname', person_data.get('last_name', '')),
                'gender': person_data.get('gender', 'U'),
                'maiden_name': person_data.get('maiden_name'),
                'occupation': person_data.get('occupation', person_data.get('occupations')),
                'tags': person_data.get('tags', []),
                'notes': person_data.get('notes') or None
            }

            # Handle birth date (used for event creation only, not stored on person)
            birth_date = None
            if 'birth_date' in person_data and person_data['birth_date']:
                birth_date = person_data['birth_date']
            elif 'birth_year_estimate' in person_data and person_data['birth_year_estimate']:
                birth_date = {'year': person_data['birth_year_estimate'], 'month': None, 'day': None, 'circa': True}

            # Handle death date (used for event creation only, not stored on person)
            death_date = None
            if 'death_date' in person_data and person_data['death_date']:
                death_date = person_data['death_date']
            elif 'death_year_estimate' in person_data and person_data['death_year_estimate']:
                death_date = {'year': person_data['death_year_estimate'], 'month': None, 'day': None, 'circa': True}

            # Add person to data
            persons[new_id] = new_person

            # Step 9: ALWAYS create birth event for every person
            created_events = []
            birth_event_id = self.get_next_event_id(events)

            # Handle place
            place_id = None
            if person_data.get('place_of_birth'):
                place_id = self.find_or_create_place(places, person_data['place_of_birth'])

            birth_event = {
                'id': birth_event_id,
                'type': 'birth',
                'date': birth_date,
                'place_id': place_id,
                'description': f"Birth of {new_person['first_name']} {new_person['last_name']}",
                'tags': [],
                'links': [],
                'notes': 'Auto-generated from person creation'
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
                    place_id = self.find_or_create_place(places, person_data['place_of_death'])

                death_event = {
                    'id': death_event_id,
                    'type': 'death',
                    'date': death_date,
                    'place_id': place_id,
                    'description': f"Death of {new_person['first_name']} {new_person['last_name']}",
                    'tags': [],
                    'links': [],
                    'notes': 'Auto-generated from person creation'
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

            # Save updated data
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

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
            # Load current data
            data_path = 'data/genealogy_new_model.json'
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

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
                        place_id = self.find_or_create_place(places, person_data['place_of_birth'])
                        events[birth_event_id]['place_id'] = place_id
                        print(f"  [OK] Synced birth place to event {birth_event_id}")

                    updated_events.append(birth_event_id)
                else:
                    # Create birth event if data provided
                    if person_data.get('birth_date') or person_data.get('place_of_birth'):
                        birth_event_id = self.get_next_event_id(events)

                        place_id = None
                        if person_data.get('place_of_birth'):
                            place_id = self.find_or_create_place(places, person_data['place_of_birth'])

                        events[birth_event_id] = {
                            'id': birth_event_id,
                            'type': 'birth',
                            'date': person_data.get('birth_date'),
                            'place_id': place_id,
                            'description': f"Birth of {person['first_name']} {person['last_name']}",
                            'tags': [],
                            'links': [],
                            'notes': 'Auto-generated from person update'
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
                        place_id = self.find_or_create_place(places, person_data['place_of_death'])
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
                            place_id = self.find_or_create_place(places, person_data['place_of_death'])

                        events[death_event_id] = {
                            'id': death_event_id,
                            'type': 'death',
                            'date': person_data.get('death_date'),
                            'place_id': place_id,
                            'description': f"Death of {person['first_name']} {person['last_name']}",
                            'tags': [],
                            'links': [],
                            'notes': 'Auto-generated from person update'
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

            # Save updated data
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

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
            # Load current data
            data_path = 'data/genealogy_new_model.json'
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

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

            # Check for and delete empty events
            events_deleted = []
            for event_id in events_to_check:
                # Count remaining participants
                remaining_participants = sum(1 for ep in event_participations.values()
                                           if ep['event_id'] == event_id)
                if remaining_participants == 0:
                    events.pop(event_id, None)
                    events_deleted.append(event_id)

            # Save updated data
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

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
            # Load current data
            data_path = 'data/genealogy_new_model.json'
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

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

            # Save updated data
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

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

    def find_death_event_for_person(self, events, event_participations, person_id):
        """Find death event where person is deceased"""
        for ep in event_participations.values():
            if ep['person_id'] == person_id and ep['role'] == 'deceased':
                event = events.get(ep['event_id'])
                if event and event['type'] == 'death':
                    return ep['event_id']
        return None

    def gedcom_lookup(self, search_data):
        """Search for persons in converted GEDCOM data with full details"""
        try:
            search_term = search_data.get('search', '').strip().lower()
            if not search_term:
                return {'success': False, 'error': 'No search term provided'}

            # Load converted GEDCOM JSON data
            gedcom_json_path = 'data/gedcom_model.json'
            if not os.path.exists(gedcom_json_path):
                return {'success': False, 'error': 'GEDCOM data file not found. Run convert_gedcom_to_model.py first.'}

            with open(gedcom_json_path, 'r', encoding='utf-8') as f:
                gedcom_data = json.load(f)

            gedcom_persons = gedcom_data['persons']
            gedcom_events = gedcom_data['events']
            gedcom_participations = gedcom_data['event_participations']
            gedcom_places = gedcom_data.get('places', {})

            # Build helper indexes
            # Index: person_id -> list of event_participations
            person_to_events = {}
            for ep_id, ep in gedcom_participations.items():
                person_id = ep['person_id']
                if person_id not in person_to_events:
                    person_to_events[person_id] = []
                person_to_events[person_id].append(ep)

            # Search for matching persons (fuzzy matching)
            matches = []
            search_parts = search_term.split()  # Split search into parts

            for person_id, person in gedcom_persons.items():
                first_name = person.get('first_name', '').lower()
                last_name = person.get('last_name', '').lower()
                full_name = f"{first_name} {last_name}"

                # Check if search term matches: all parts must be found in either first or last name
                match = True
                for part in search_parts:
                    if not (part in first_name or part in last_name or part in full_name):
                        match = False
                        break

                if match:
                    # Extract year and place from birth/death dates
                    birth_year = person.get('birth_date', {}).get('year') if person.get('birth_date') else None
                    death_year = person.get('death_date', {}).get('year') if person.get('death_date') else None

                    # Find birth and death places from events
                    birth_place = None
                    death_place = None
                    parents = {'father': None, 'mother': None}
                    children = []
                    spouses = []
                    all_events = []

                    person_events = person_to_events.get(person_id, [])
                    for ep in person_events:
                        event = gedcom_events.get(ep['event_id'])
                        if not event:
                            continue

                        event_info = {
                            'id': event['id'],
                            'type': event['type'],
                            'date': event.get('date'),
                            'place': gedcom_places.get(event.get('place_id'), {}).get('name') if event.get('place_id') else None
                        }

                        # Get birth event and place
                        if event['type'] == 'birth' and ep['role'] == 'child':
                            if event.get('place_id'):
                                place = gedcom_places.get(event['place_id'])
                                if place:
                                    birth_place = place.get('name')

                            # Find parents in this birth event
                            for other_ep in gedcom_participations.values():
                                if other_ep['event_id'] == event['id']:
                                    if other_ep['role'] == 'father':
                                        father = gedcom_persons.get(other_ep['person_id'])
                                        if father:
                                            parents['father'] = {
                                                'id': other_ep['person_id'],
                                                'name': f"{father.get('first_name', '')} {father.get('last_name', '')}".strip()
                                            }
                                    elif other_ep['role'] == 'mother':
                                        mother = gedcom_persons.get(other_ep['person_id'])
                                        if mother:
                                            parents['mother'] = {
                                                'id': other_ep['person_id'],
                                                'name': f"{mother.get('first_name', '')} {mother.get('last_name', '')}".strip()
                                            }

                        # Get death event and place
                        elif event['type'] == 'death' and ep['role'] == 'deceased':
                            if event.get('place_id'):
                                place = gedcom_places.get(event['place_id'])
                                if place:
                                    death_place = place.get('name')

                        # Get children (birth events where this person is parent)
                        elif event['type'] == 'birth' and ep['role'] in ['father', 'mother']:
                            for other_ep in gedcom_participations.values():
                                if other_ep['event_id'] == event['id'] and other_ep['role'] == 'child':
                                    child = gedcom_persons.get(other_ep['person_id'])
                                    if child:
                                        child_info = {
                                            'id': other_ep['person_id'],
                                            'name': f"{child.get('first_name', '')} {child.get('last_name', '')}".strip()
                                        }
                                        if child_info not in children:
                                            children.append(child_info)

                        # Get spouses (marriage events)
                        elif event['type'] == 'marriage' and ep['role'] in ['groom', 'bride']:
                            for other_ep in gedcom_participations.values():
                                if other_ep['event_id'] == event['id'] and other_ep['role'] in ['groom', 'bride'] and other_ep['person_id'] != person_id:
                                    spouse = gedcom_persons.get(other_ep['person_id'])
                                    if spouse:
                                        spouse_info = {
                                            'id': other_ep['person_id'],
                                            'name': f"{spouse.get('first_name', '')} {spouse.get('last_name', '')}".strip()
                                        }
                                        if spouse_info not in spouses:
                                            spouses.append(spouse_info)

                        all_events.append(event_info)

                    # Build match result with comprehensive data
                    match = {
                        'gedcom_id': person_id,
                        'given_name': person.get('first_name', ''),
                        'surname': person.get('last_name', ''),
                        'maiden_name': person.get('maiden_name'),
                        'gender': person.get('gender', ''),
                        'birth_year': birth_year,
                        'death_year': death_year,
                        'birth_place': birth_place,
                        'death_place': death_place,
                        'occupation': person.get('occupation'),
                        'birth_year_estimate': birth_year,  # For compatibility
                        'death_year_estimate': death_year,  # For compatibility
                        'father_name': parents['father']['name'] if parents['father'] else None,
                        'mother_name': parents['mother']['name'] if parents['mother'] else None,
                        'parents': parents,
                        'children': children,
                        'spouses': spouses,
                        'events': all_events
                    }
                    matches.append(match)

            # Sort by name
            matches.sort(key=lambda x: (x.get('surname', ''), x.get('given_name', '')))

            print(f"[OK] GEDCOM lookup for '{search_term}': found {len(matches)} matches")

            return {
                'success': True,
                'matches': matches,
                'count': len(matches)
            }

        except Exception as e:
            print(f"[ERR] Error looking up GEDCOM: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def get_gedcom_person(self, person_id):
        """Get a single person from GEDCOM by ID"""
        try:
            # Load GEDCOM data
            with open('data/gedcom_model.json', 'r', encoding='utf-8') as f:
                gedcom_data = json.load(f)

            gedcom_persons = gedcom_data.get('persons', {})

            if person_id not in gedcom_persons:
                return {
                    'success': False,
                    'error': f'Person {person_id} not found in GEDCOM'
                }

            person = gedcom_persons[person_id]

            print(f"[OK] Fetched GEDCOM person: {person_id}")

            return {
                'success': True,
                'person': person
            }

        except Exception as e:
            print(f"[ERR] Error fetching GEDCOM person: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }


    def get_next_person_id(self, persons):
        """Generate next person ID"""
        max_id = max([int(p['id'][1:]) for p in persons.values()], default=0)
        return f"P{(max_id + 1):04d}"

    def get_next_relationship_id(self, relationships):
        """Generate next relationship ID"""
        max_id = max([int(r['id'][1:]) for r in relationships.values()], default=0)
        return f"R{(max_id + 1):04d}"

    def determine_parent_role(self, person):
        """Determine parent role based on gender"""
        return 'father' if person.get('gender') == 'M' else 'mother'

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

    def find_or_create_place(self, places, place_name):
        """Find existing place by name or create new one"""
        # Search for existing place
        for place_id, place in places.items():
            if place.get('name', '').lower() == place_name.lower():
                return place_id

        # Create new place
        max_id = max([int(p['id'][2:]) for p in places.values()], default=0) if places else 0
        new_place_id = f"PL{(max_id + 1):04d}"
        places[new_place_id] = {
            'id': new_place_id,
            'name': place_name,
            'type': 'settlement'
        }
        print(f"  [OK] Created new place: {new_place_id} - {place_name}")
        return new_place_id

    def find_birth_event_for_person(self, events, event_participations, person_id):
        """Find birth event where person is the child"""
        for ep in event_participations.values():
            if ep['person_id'] == person_id and ep['role'] == 'child':
                event = events.get(ep['event_id'])
                if event and event['type'] == 'birth':
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
                    'description': f"Marriage of {father['first_name']} {father['last_name']} and {mother['first_name']} {mother['last_name']}",
                    'tags': [],
                    'links': [],
                    'notes': f'Auto-generated from birth event {birth_event_id} (Step 30)'
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

    def add_relationship(self, rel_data):
        """Add a new EVENT-BASED relationship between two persons (Step 10)"""
        try:
            # Load current data (NEW MODEL)
            data_path = 'data/genealogy_new_model.json'
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

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
                        'description': f"Birth of {child['first_name']} {child['last_name']}",
                        'tags': [],
                        'links': [],
                        'notes': 'Auto-generated from relationship addition'
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
                        'description': f"Birth of {child['first_name']} {child['last_name']}",
                        'tags': [],
                        'links': [],
                        'notes': 'Auto-generated from relationship addition'
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
                        'description': f"Marriage of {person1['first_name']} {person1['last_name']} and {person2['first_name']} {person2['last_name']}",
                        'tags': [],
                        'links': [],
                        'notes': 'Auto-generated from relationship addition'
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
                        'description': f"Birth of {child['first_name']} {child['last_name']}",
                        'tags': [],
                        'links': [],
                        'notes': 'Auto-generated from relationship addition'
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

            # Save updated data
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

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
            # Load current data
            data_path = 'data/genealogy_new_model.json'
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            persons = data['persons']
            places = data.get('places', {})
            events = data['events']
            event_participations = data.get('event_participations', {})

            # Generate event ID
            max_event_id = max([int(e['id'][1:]) for e in events.values()], default=0)
            event_id = f"E{(max_event_id + 1):04d}"

            # Handle place
            place_id = None
            if event_data.get('place_name'):
                place_name = event_data['place_name']
                house_number = event_data.get('house_number', '')

                # Find existing place or create new one
                place_id = None
                for pid, place in places.items():
                    if place['name'] == place_name and place.get('house_number', '') == house_number:
                        place_id = pid
                        break

                if not place_id:
                    # Create new place
                    max_place_id = max([int(p['id'][2:]) for p in places.values()], default=0) if places else 0
                    place_id = f"PL{(max_place_id + 1):04d}"
                    places[place_id] = {
                        'id': place_id,
                        'name': place_name,
                        'house_number': house_number
                    }

            # Create event
            new_event = {
                'id': event_id,
                'type': event_data['type'],
                'title': event_data.get('title', None),
                'date': event_data['date'],
                'place_id': place_id,
                'content': '',  # Will be generated from participants
                'tags': event_data.get('tags', []),
                'links': event_data.get('links', []),
                'notes': event_data.get('notes', '')
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

                    new_person = {
                        'id': person_id,
                        'first_name': participant['first_name'],
                        'last_name': participant['last_name'],
                        'maiden_name': participant.get('maiden_name'),
                        'gender': inferred_gender,
                        'occupation': participant.get('occupation')
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
                                    'occupation': None
                                }

                                persons[parent_id] = parent_person
                                new_persons.append(parent_person)
                                print(f"  [OK] Created parent: {parent_id} - {parent_person['first_name']} {parent_person['last_name']}")

                            created_parents[parent_type] = parent_id

                    # Create birth event if we have age-based date OR parents were specified
                    if birth_date or created_parents['mother'] or created_parents['father']:
                        # Create birth event for the child
                        max_event_id = max([int(e['id'][1:]) for e in events.values()], default=0)
                        birth_event_id = f"E{(max_event_id + 1):04d}"

                        birth_event = {
                            'id': birth_event_id,
                            'type': 'birth',
                            'date': birth_date,
                            'place_id': None,
                            'description': f"Birth of {new_person['first_name']} {new_person['last_name']}",
                            'tags': [],
                            'links': [],
                            'notes': 'Auto-generated from event with parent data',
                            'content': ''
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
                        for parent_type, parent_id in created_parents.items():
                            if parent_id:
                                max_ep_id += 1
                                ep_id = f"EP{max_ep_id:04d}"
                                event_participations[ep_id] = {
                                    'id': ep_id,
                                    'event_id': birth_event_id,
                                    'person_id': parent_id,
                                    'role': parent_type
                                }

                        print(f"  [OK] Created birth event: {birth_event_id} for {person_id} with parents")

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
                                'description': f"Marriage of {father['first_name']} {father['last_name']} and {mother['first_name']} {mother['last_name']}",
                                'tags': [],
                                'links': [],
                                'notes': 'Auto-generated from child birth event',
                                'content': ''
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

                # Update maiden_name for existing persons if provided
                if is_existing_person and person_id and person_id in persons:
                    maiden_name = participant.get('maiden_name')
                    if maiden_name:
                        persons[person_id]['maiden_name'] = maiden_name
                        print(f"  [OK] Updated maiden_name for existing person {person_id}: {maiden_name}")

                if person_id:
                    # Create event participation
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

            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

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
            # Load current data
            data_path = 'data/genealogy_new_model.json'
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            event_id = event_data['event_id']
            events = data['events']
            places = data.get('places', {})
            event_participations = data.get('event_participations', {})
            persons = data['persons']

            if event_id not in events:
                return {'success': False, 'error': f'Event {event_id} not found'}

            # Update event basic info
            event = events[event_id]
            event['type'] = event_data['type']
            event['title'] = event_data.get('title', None)
            event['date'] = event_data['date']
            event['tags'] = event_data.get('tags', [])
            event['links'] = event_data.get('links', [])
            event['notes'] = event_data.get('notes', '')

            # Handle place
            place_id = None
            if event_data.get('place_name'):
                place_name = event_data['place_name']
                house_number = event_data.get('house_number', '')

                # Find existing place or create new one
                for pid, place in places.items():
                    if place['name'] == place_name and place.get('house_number', '') == house_number:
                        place_id = pid
                        break

                if not place_id:
                    max_place_id = max([int(p['id'][2:]) for p in places.values()], default=0) if places else 0
                    place_id = f"PL{(max_place_id + 1):04d}"
                    places[place_id] = {
                        'id': place_id,
                        'name': place_name,
                        'house_number': house_number
                    }

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
                        'occupation': participant.get('occupation')
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
                                    'occupation': None
                                }

                                persons[parent_id] = parent_person
                                new_persons.append(parent_person)
                                print(f"  [OK] Created parent: {parent_id} - {parent_person['first_name']} {parent_person['last_name']}")

                            created_parents[parent_type] = parent_id

                    # Create birth event if we have age-based date OR parents were specified
                    if birth_date or created_parents['mother'] or created_parents['father']:
                        # Create birth event for the child
                        max_event_id = max([int(e['id'][1:]) for e in events.values()], default=0)
                        birth_event_id = f"E{(max_event_id + 1):04d}"

                        birth_event = {
                            'id': birth_event_id,
                            'type': 'birth',
                            'date': birth_date,
                            'place_id': None,
                            'description': f"Birth of {new_person['first_name']} {new_person['last_name']}",
                            'tags': [],
                            'links': [],
                            'notes': 'Auto-generated from event with parent data',
                            'content': ''
                        }
                        events[birth_event_id] = birth_event

                        # Add child as participant
                        max_ep_id_temp = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)
                        max_ep_id_temp += 1
                        ep_id = f"EP{max_ep_id_temp:04d}"
                        event_participations[ep_id] = {
                            'id': ep_id,
                            'event_id': birth_event_id,
                            'person_id': person_id,
                            'role': 'child'
                        }

                        # Add parents as participants
                        for parent_type, parent_id_temp in created_parents.items():
                            if parent_id_temp:
                                max_ep_id_temp += 1
                                ep_id = f"EP{max_ep_id_temp:04d}"
                                event_participations[ep_id] = {
                                    'id': ep_id,
                                    'event_id': birth_event_id,
                                    'person_id': parent_id_temp,
                                    'role': parent_type
                                }

                        print(f"  [OK] Created birth event: {birth_event_id} for {person_id} with parents")

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
                                'description': f"Marriage of {father['first_name']} {father['last_name']} and {mother['first_name']} {mother['last_name']}",
                                'tags': [],
                                'links': [],
                                'notes': 'Auto-generated from child birth event',
                                'content': ''
                            }
                            events[marriage_event_id] = marriage_event

                            # Add parents as bride and groom
                            max_ep_id_temp = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)
                            max_ep_id_temp += 1
                            ep_id = f"EP{max_ep_id_temp:04d}"
                            event_participations[ep_id] = {
                                'id': ep_id,
                                'event_id': marriage_event_id,
                                'person_id': created_parents['father'],
                                'role': 'groom'
                            }

                            max_ep_id_temp += 1
                            ep_id = f"EP{max_ep_id_temp:04d}"
                            event_participations[ep_id] = {
                                'id': ep_id,
                                'event_id': marriage_event_id,
                                'person_id': created_parents['mother'],
                                'role': 'bride'
                            }

                            print(f"  [OK] Created marriage event: {marriage_event_id} between parents")

                # Update maiden_name for existing persons if provided
                if is_existing_person and person_id and person_id in persons:
                    maiden_name = participant.get('maiden_name')
                    if maiden_name:
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

            # Save data
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"[OK] Updated event: {event_id}")
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
                        'description': f"Birth of {child.get('first_name', '')} {child.get('last_name', '')}",
                        'tags': [],
                        'links': [],
                        'notes': 'Auto-generated for parent synchronization',
                        'content': ''
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
                        # Update existing birth event if it doesn't have a year
                        birth_event = events[birth_event_id]
                        if not birth_event.get('date') or not birth_event['date'].get('year'):
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
                            'content': f"Birth of {person.get('first_name', '')} {person.get('last_name', '')}",
                            'tags': [],
                            'links': [],
                            'notes': f'Auto-generated from age {age} in event {event_id}'
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

    def generate_parent_marriages(self):
        """
        Step 18: Parse all birth events and create synthetic marriage events
        between mothers and fathers if they don't exist already.
        """
        try:
            # Load current data
            data_path = 'data/genealogy_new_model.json'
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            persons = data['persons']
            events = data['events']
            event_participations = data.get('event_participations', {})

            # First pass: collect all parent pairs that need marriage events
            parent_pairs_to_marry = []

            for event_id, event in events.items():
                if event['type'] != 'birth':
                    continue

                # Find mother and father in this birth event
                mother_id = None
                father_id = None

                for ep in event_participations.values():
                    if ep['event_id'] == event_id:
                        if ep['role'] == 'mother':
                            mother_id = ep['person_id']
                        elif ep['role'] == 'father':
                            father_id = ep['person_id']

                # If both parents exist, check if they have a marriage event
                if mother_id and father_id:
                    # Check if marriage event already exists between them
                    marriage_exists = False
                    for ev_id, ev in events.items():
                        if ev['type'] == 'marriage':
                            participants = [ep['person_id'] for ep in event_participations.values()
                                          if ep['event_id'] == ev_id and ep['role'] in ['bride', 'groom']]
                            if mother_id in participants and father_id in participants:
                                marriage_exists = True
                                break

                    if not marriage_exists:
                        # Check if we haven't already queued this pair
                        pair = tuple(sorted([mother_id, father_id]))
                        if pair not in [tuple(sorted([p['mother'], p['father']])) for p in parent_pairs_to_marry]:
                            parent_pairs_to_marry.append({
                                'mother': mother_id,
                                'father': father_id
                            })

            # Second pass: create marriage events for collected pairs
            created_marriages = []
            for pair in parent_pairs_to_marry:
                mother_id = pair['mother']
                father_id = pair['father']

                # Create marriage event
                max_event_id = max([int(e['id'][1:]) for e in events.values()], default=0)
                marriage_event_id = f"E{(max_event_id + 1):04d}"

                mother = persons.get(mother_id, {})
                father = persons.get(father_id, {})

                marriage_event = {
                    'id': marriage_event_id,
                    'type': 'marriage',
                    'date': None,
                    'place_id': None,
                    'description': f"Marriage of {father.get('first_name', '')} {father.get('last_name', '')} and {mother.get('first_name', '')} {mother.get('last_name', '')}",
                    'tags': [],
                    'links': [],
                    'notes': 'Auto-generated from birth records (Step 30)',
                    'content': ''
                }
                events[marriage_event_id] = marriage_event

                # Add participants
                max_ep_id = max([int(ep['id'][2:]) for ep in event_participations.values()], default=0)

                # Add groom
                max_ep_id += 1
                ep_id = f"EP{max_ep_id:04d}"
                event_participations[ep_id] = {
                    'id': ep_id,
                    'event_id': marriage_event_id,
                    'person_id': father_id,
                    'role': 'groom'
                }

                # Add bride
                max_ep_id += 1
                ep_id = f"EP{max_ep_id:04d}"
                event_participations[ep_id] = {
                    'id': ep_id,
                    'event_id': marriage_event_id,
                    'person_id': mother_id,
                    'role': 'bride'
                }

                created_marriages.append({
                    'event_id': marriage_event_id,
                    'father': f"{father.get('first_name', '')} {father.get('last_name', '')} ({father_id})",
                    'mother': f"{mother.get('first_name', '')} {mother.get('last_name', '')} ({mother_id})"
                })

                print(f"  [OK] Created marriage {marriage_event_id}: {father_id} + {mother_id}")

            # Save data
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"[OK] Generated {len(created_marriages)} synthetic marriage events")

            return {
                'success': True,
                'created_count': len(created_marriages),
                'marriages': created_marriages,
                'message': f'Successfully created {len(created_marriages)} marriage events from birth records'
            }

        except Exception as e:
            print(f"[ERR] Error generating parent marriages: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def sync_all_ages_to_birth_years_migration(self):
        """
        Step 21 Migration: Process all existing events and calculate birth years from ages.
        """
        try:
            # Load current data
            data_path = 'data/genealogy_new_model.json'
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            persons = data['persons']
            events = data['events']
            event_participations = data.get('event_participations', {})

            synced_count = 0

            # Build a map of event_id -> event_year for quick lookup
            event_years = {}
            for event_id, event in events.items():
                if event.get('date') and event['date'].get('year'):
                    event_years[event_id] = event['date']['year']

            # Process all event participations looking for ages
            for ep in event_participations.values():
                # Skip if no age data
                age = ep.get('age')
                if not age:
                    continue

                event_id = ep['event_id']
                person_id = ep['person_id']

                # Skip if event has no year or person doesn't exist
                if event_id not in event_years or person_id not in persons:
                    continue

                event_year = event_years[event_id]
                calculated_birth_year = event_year - age

                # Find birth event for this person
                birth_event_id = self.find_birth_event_for_person(events, event_participations, person_id)

                if birth_event_id:
                    birth_event = events[birth_event_id]
                    # Only update if birth event doesn't have a year
                    if not birth_event.get('date') or not birth_event['date'].get('year'):
                        birth_event['date'] = {
                            'year': calculated_birth_year,
                            'month': None,
                            'day': None,
                            'circa': True
                        }
                        synced_count += 1
                        print(f"  [OK] Calculated birth year {calculated_birth_year} for {person_id} from age {age} in event {event_id}")

            # Save data
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"[OK] Synced birth years for {synced_count} persons from ages")

            return {
                'success': True,
                'synced_count': synced_count,
                'message': f'Successfully calculated birth years for {synced_count} persons from event ages'
            }

        except Exception as e:
            print(f"[ERR] Error syncing ages to birth years: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def score_person_completeness(self, person_id, persons, event_participations):
        """Score how complete a person's data is (Step 31 helper)"""
        if person_id not in persons:
            return 0

        person = persons[person_id]
        score = 0

        # Data completeness (birth/death dates are now in events, score via event count below)
        if person.get('gender') and person['gender'] != 'U':
            score += 5
        if person.get('occupation'):
            score += 5
        if person.get('maiden_name'):
            score += 3

        # Count events participated in
        num_events = sum(1 for ep in event_participations.values() if ep['person_id'] == person_id)
        score += num_events * 2

        return score

    def merge_persons(self, keep_id, delete_id, persons, event_participations, merge_log):
        """Merge two person entities, keeping the one with more complete data (Step 31)"""
        if keep_id not in persons or delete_id not in persons:
            return False

        keep_person = persons[keep_id]
        delete_person = persons[delete_id]

        # Merge data (keep most complete)
        keep_person['gender'] = keep_person.get('gender') if keep_person.get('gender') != 'U' else delete_person.get('gender')
        keep_person['occupation'] = keep_person.get('occupation') or delete_person.get('occupation')
        keep_person['maiden_name'] = keep_person.get('maiden_name') or delete_person.get('maiden_name')

        # Update all event participations
        for ep in event_participations.values():
            if ep['person_id'] == delete_id:
                ep['person_id'] = keep_id

        # Remove duplicate participations (same person, same event, same role)
        seen = {}
        to_delete = []
        for ep_id, ep in event_participations.items():
            key = (ep['event_id'], ep['person_id'], ep['role'])
            if key in seen:
                # Duplicate found, mark for deletion
                to_delete.append(ep_id)
            else:
                seen[key] = ep_id

        for ep_id in to_delete:
            del event_participations[ep_id]

        # Delete the duplicate person
        del persons[delete_id]

        # Log the merge
        merge_log.append({
            'kept_id': keep_id,
            'kept_name': f"{keep_person['first_name']} {keep_person['last_name']}",
            'deleted_id': delete_id,
            'deleted_name': f"{delete_person['first_name']} {delete_person['last_name']}",
            'removed_duplicate_participations': len(to_delete)
        })

        return True

    def deduplicate_witnesses_godparents(self):
        """
        Step 31: Find and merge witnesses and godparents with matching names
        within the same birth event.
        """
        try:
            # Load current data
            data_path = 'data/genealogy_new_model.json'
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            persons = data['persons']
            events = data['events']
            event_participations = data.get('event_participations', {})

            merge_log = []
            merges_performed = 0

            # Scan all birth events
            for event_id, event in events.items():
                if event['type'] != 'birth':
                    continue

                # Get all participants in this event
                participants = [ep for ep in event_participations.values() if ep['event_id'] == event_id]

                # Separate witnesses and godparents
                witnesses = [ep for ep in participants if ep['role'] == 'witness']
                godparents = [ep for ep in participants if 'god' in ep['role'].lower()]

                # Check for name matches
                for witness_ep in witnesses:
                    witness_id = witness_ep['person_id']
                    if witness_id not in persons:
                        continue
                    witness = persons[witness_id]
                    witness_name = (witness['first_name'].lower(), witness['last_name'].lower())

                    for godparent_ep in godparents:
                        godparent_id = godparent_ep['person_id']
                        if godparent_id not in persons or godparent_id == witness_id:
                            continue
                        godparent = persons[godparent_id]
                        godparent_name = (godparent['first_name'].lower(), godparent['last_name'].lower())

                        # Case-insensitive name match
                        if witness_name == godparent_name:
                            # Score each person
                            witness_score = self.score_person_completeness(witness_id, persons, event_participations)
                            godparent_score = self.score_person_completeness(godparent_id, persons, event_participations)

                            # Keep the one with higher score
                            keep_id, delete_id = (witness_id, godparent_id) if witness_score >= godparent_score else (godparent_id, witness_id)

                            print(f"  Merging {delete_id} into {keep_id} in event {event_id}: {witness['first_name']} {witness['last_name']}")

                            # Perform merge
                            if self.merge_persons(keep_id, delete_id, persons, event_participations, merge_log):
                                merges_performed += 1
                                break  # Move to next witness (avoid modifying list while iterating)

            # Save data
            if merges_performed > 0:
                with open(data_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"[OK] Deduplicated {merges_performed} witness/godparent pairs")

            return {
                'success': True,
                'merges_performed': merges_performed,
                'merge_log': merge_log,
                'message': f'Successfully merged {merges_performed} duplicate witness/godparent persons'
            }

        except Exception as e:
            print(f"[ERR] Error deduplicating witnesses/godparents: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }


    def geneteka_import(self, first_name, last_name, record_type='birth'):
        """Proxy request to Geneteka API and return parsed records (birth/marriage/death)"""
        import urllib.request
        import urllib.parse
        import re

        type_config = {
            'birth':    ('B', '3382'),
            'marriage': ('S', '3560'),
            'death':    ('D', '3384'),
        }
        bdm, rid = type_config.get(record_type, ('B', '3382'))

        def extract_uwagi(html):
            notes_parts = re.findall(r'<img[^>]+title="([^"]*)"', html)
            return ' | '.join(t.strip() for t in notes_parts if t.strip())

        def extract_links(html):
            return re.findall(r'href="(https?://[^"]+)"', html)

        def strip_html(text):
            return re.sub(r'<[^>]+>', '', text).strip()

        def parse_rodzice(rodzice):
            """Parse 'FatherName, MotherName MotherMaiden' into components"""
            if not rodzice or not rodzice.strip():
                return {'father_name': '', 'mother_name': '', 'mother_maiden': ''}
            parts = rodzice.split(',', 1)
            father_name = parts[0].strip()
            mother_part = parts[1].strip() if len(parts) > 1 else ''
            mother_parts = mother_part.split()
            mother_name = mother_parts[0] if mother_parts else ''
            mother_maiden = mother_parts[1] if len(mother_parts) > 1 else ''
            return {'father_name': father_name, 'mother_name': mother_name, 'mother_maiden': mother_maiden}

        try:
            import http.cookiejar
            encoded_last = urllib.parse.quote(last_name)
            encoded_first = urllib.parse.quote(first_name)

            # Build session using a cookie jar so the index page sets cookies
            # before we hit the API (Geneteka returns empty data without a session)
            cj = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
            common_headers = [
                ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
                ('Accept-Language', 'pl,en;q=0.9'),
            ]
            # Step 1: visit the HTML search page to establish the session
            index_url = (
                f"https://geneteka.genealodzy.pl/index.php"
                f"?op=gt&lang=pol&bdm={bdm}&w=13sk&rid={rid}"
                f"&search_lastname={encoded_last}&search_name={encoded_first}"
                f"&search_lastname2=&search_name2=&from_date=&to_date="
            )
            index_req = urllib.request.Request(index_url, headers={
                'User-Agent': common_headers[0][1],
                'Accept': 'text/html',
                'Accept-Language': common_headers[1][1],
            })
            with opener.open(index_req, timeout=15) as _:
                pass  # just need the cookies

            # Step 2: call the JSON API with the session cookies
            url = (
                f"https://geneteka.genealodzy.pl/api/getAct.php"
                f"?op=gt&lang=pol&bdm={bdm}&w=13sk&rid={rid}"
                f"&search_lastname={encoded_last}&search_name={encoded_first}"
                f"&search_lastname2=&search_name2=&from_date=&to_date="
                f"&draw=1&start=0&length=100"
            )
            req = urllib.request.Request(url, headers={
                'User-Agent': common_headers[0][1],
                'Referer': index_url,
                'Accept': 'application/json',
                'Accept-Language': common_headers[1][1],
                'X-Requested-With': 'XMLHttpRequest',
            })

            with opener.open(req, timeout=15) as response:
                raw = response.read().decode('utf-8')

            data = json.loads(raw)
            records = []

            for row in data.get('data', []):
                if record_type == 'marriage':
                    # 10 columns: rok, akt, groom_name, groom_surname, groom_parents,
                    #              bride_name, bride_surname, bride_parents, place, uwagi
                    if len(row) < 9:
                        continue
                    uwagi_html = row[9] if len(row) > 9 else ''
                    records.append({
                        'rok': strip_html(row[0]).strip(),
                        'akt': strip_html(row[1]).strip(),
                        'imie_pana': strip_html(row[2]).strip(),
                        'nazwisko_pana': strip_html(row[3]).strip(),
                        'rodzice_pana': strip_html(row[4]).strip(),
                        'imie_pani': strip_html(row[5]).strip(),
                        'nazwisko_pani': strip_html(row[6]).strip(),
                        'rodzice_pani': strip_html(row[7]).strip(),
                        'miejscowosc': strip_html(row[8]).strip(),
                        'uwagi': extract_uwagi(uwagi_html),
                        'links': extract_links(uwagi_html),
                        'rodzice_pana_parsed': parse_rodzice(strip_html(row[4]).strip()),
                        'rodzice_pani_parsed': parse_rodzice(strip_html(row[7]).strip()),
                    })
                elif record_type == 'death':
                    # 9 columns: rok, akt, name, surname (may have HTML), father, mother, mother_maiden, place, uwagi
                    if len(row) < 8:
                        continue
                    uwagi_html = row[8] if len(row) > 8 else ''
                    records.append({
                        'rok': strip_html(row[0]).strip(),
                        'akt': strip_html(row[1]).strip(),
                        'imie': strip_html(row[2]).strip(),
                        'nazwisko': strip_html(row[3]).strip(),
                        'imie_ojca': strip_html(row[4]).strip(),
                        'imie_matki': strip_html(row[5]).strip(),
                        'nazwisko_matki': strip_html(row[6]).strip(),
                        'miejscowosc': strip_html(row[7]).strip(),
                        'uwagi': extract_uwagi(uwagi_html),
                        'links': extract_links(uwagi_html),
                    })
                else:
                    # birth: 10 columns: rok, akt, child_name, surname, father, mother, mother_maiden, parish, place, uwagi
                    # Some older/incomplete records have fewer columns; use empty string for missing fields.
                    if len(row) < 2:
                        continue
                    def col(i): return strip_html(row[i]).strip() if len(row) > i else ''
                    uwagi_html = row[9] if len(row) > 9 else ''
                    records.append({
                        'rok': col(0),
                        'akt': col(1),
                        'imie_dziecka': col(2),
                        'nazwisko': col(3),
                        'imie_ojca': col(4),
                        'imie_matki': col(5),
                        'nazwisko_matki': col(6),
                        'parafia': col(7),
                        'miejscowosc': col(8),
                        'uwagi': extract_uwagi(uwagi_html),
                        'links': extract_links(uwagi_html),
                    })

            return {
                'success': True,
                'records': records,
                'total': data.get('recordsTotal', len(records)),
            }

        except Exception as e:
            print(f"[ERR] Geneteka import error: {e}")
            return {'success': False, 'error': str(e), 'records': []}


def run_server(port=8001):
    """Start the genealogy server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, GenealogyServerHandler)

    print("=" * 70)
    print("Genealogy Editor Server")
    print("=" * 70)
    print(f"Server running at: http://localhost:{port}/")
    print(f"Web interface: http://localhost:{port}/web/")
    print("Press Ctrl+C to stop")
    print("=" * 70)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")


if __name__ == '__main__':
    run_server(8001)
