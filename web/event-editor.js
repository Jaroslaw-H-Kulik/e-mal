// Event Editor - Add and Edit Events

class EventEditor {
    constructor(app) {
        this.app = app;
        this.currentEventType = null;
        this.currentPersonId = null;
        this.editingEventId = null;
        this.setupEditor();
    }

    setupEditor() {
        // Add modal HTML to page
        const modalHTML = `
            <!-- Event Editor Modal -->
            <div id="event-editor-modal" class="modal">
                <div class="modal-content" style="max-width: 900px; max-height: 90vh; overflow-y: auto;">
                    <div class="modal-header">
                        <h2 id="event-editor-title">Add Event</h2>
                        <button class="close-modal" onclick="eventEditor.closeModal()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <!-- Event Type Selection -->
                        <div id="event-type-selection">
                            <label style="font-weight: 600; margin-bottom: 10px; display: block;">Event Type:</label>
                            <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                                <button class="btn-primary" onclick="eventEditor.selectEventType('birth')">Birth/Baptism</button>
                                <button class="btn-primary" onclick="eventEditor.selectEventType('marriage')">Marriage</button>
                                <button class="btn-primary" onclick="eventEditor.selectEventType('death')">Death</button>
                            </div>
                        </div>

                        <!-- Event Form Container -->
                        <div id="event-form-container" style="display: none;">
                            <form id="event-form">
                                <!-- Common fields -->
                                <div class="form-group">
                                    <label>Event Date</label>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
                                        <input type="number" id="event-day" placeholder="Day" min="1" max="31">
                                        <input type="number" id="event-month" placeholder="Month" min="1" max="12">
                                        <input type="number" id="event-year" placeholder="Year" min="1700" max="2100">
                                    </div>
                                </div>

                                <div class="form-group">
                                    <label>Place</label>
                                    <input type="text" id="event-place" placeholder="Settlement name" list="place-suggestions">
                                    <datalist id="place-suggestions">
                                        <option value="Małyszyn">
                                        <option value="Tychów">
                                        <option value="Bór Iłżecki">
                                        <option value="Gaworzyna">
                                        <option value="Starosiedlice">
                                        <option value="Mirzec">
                                    </datalist>
                                </div>

                                <div class="form-group">
                                    <label>House Number</label>
                                    <input type="text" id="event-house-number" placeholder="House number">
                                </div>

                                <!-- Dynamic participant fields will be inserted here -->
                                <div id="participants-container"></div>

                                <div class="form-group">
                                    <label>Tags (comma-separated)</label>
                                    <input type="text" id="event-tags" placeholder="tag1, tag2">
                                </div>

                                <div class="form-group">
                                    <label>Links (comma-separated URLs)</label>
                                    <input type="text" id="event-links" placeholder="http://example.com">
                                </div>

                                <div class="form-group">
                                    <label>Notes</label>
                                    <textarea id="event-notes" rows="3" placeholder="Additional notes"></textarea>
                                </div>

                                <div class="form-actions">
                                    <button type="submit" class="btn-primary">Save Event</button>
                                    <button type="button" class="btn-secondary" onclick="eventEditor.closeModal()">Cancel</button>
                                </div>
                            </form>

                            <!-- Event Content Editor (Step 20) -->
                            <div id="event-content-display" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 4px; border-left: 4px solid #667eea; display: none;">
                                <div class="form-group" style="margin: 0;">
                                    <label style="font-weight: 600; margin-bottom: 8px; color: #333;">Event Content/Summary:</label>
                                    <textarea id="event-content" rows="3" placeholder="Event summary text (auto-generated from participants if left empty)" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-family: inherit; font-size: 0.95rem;"></textarea>
                                    <div style="font-size: 0.85rem; color: #666; margin-top: 4px;">This content is shown in the person card events list</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Add form submit handler
        document.getElementById('event-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveEvent();
        });
    }

    openAddEventModal(personId) {
        this.currentPersonId = personId;
        this.editingEventId = null;
        document.getElementById('event-editor-title').textContent = 'Add Event';
        document.getElementById('event-type-selection').style.display = 'block';
        document.getElementById('event-form-container').style.display = 'none';
        document.getElementById('event-form').reset();
        document.getElementById('event-editor-modal').style.display = 'block';
    }

    openEditEventModal(eventId) {
        this.editingEventId = eventId;
        this.currentPersonId = this.app.selectedPerson; // Track which person's card to refresh
        const event = this.app.events[eventId];
        if (!event) return;

        document.getElementById('event-editor-title').textContent = 'Edit Event';
        document.getElementById('event-type-selection').style.display = 'none';
        document.getElementById('event-form-container').style.display = 'block';

        // Load event type and build form
        this.selectEventType(event.type, true);

        // Fill in basic event data
        if (event.date) {
            document.getElementById('event-day').value = event.date.day || '';
            document.getElementById('event-month').value = event.date.month || '';
            document.getElementById('event-year').value = event.date.year || '';
        }

        // Load place data
        if (event.place_id) {
            const place = this.app.places[event.place_id];
            if (place) {
                document.getElementById('event-place').value = place.name || '';
                document.getElementById('event-house-number').value = place.house_number || '';
            }
        }

        document.getElementById('event-tags').value = event.tags ? event.tags.join(', ') : '';
        document.getElementById('event-links').value = event.links ? event.links.join(', ') : '';
        document.getElementById('event-notes').value = event.notes || '';

        // Show modal first to ensure DOM is ready
        document.getElementById('event-editor-modal').style.display = 'block';

        // Load participants after a brief delay to ensure form is rendered
        setTimeout(() => {
            this.loadEventParticipants(eventId);
        }, 50);

        // Step 20: Display event content at bottom
        this.displayEventContent(event);
    }

    displayEventContent(event) {
        const contentDisplay = document.getElementById('event-content-display');
        const contentTextarea = document.getElementById('event-content');

        // Always show the content editor when editing an event
        contentTextarea.value = event.content || '';
        contentDisplay.style.display = 'block';
    }

    selectEventType(type, skipAnimation = false) {
        this.currentEventType = type;
        document.getElementById('event-type-selection').style.display = 'none';
        document.getElementById('event-form-container').style.display = 'block';

        // Build participants form based on type
        this.buildParticipantsForm(type);

        // Step 20: Show content editor (empty for new events)
        const contentDisplay = document.getElementById('event-content-display');
        const contentTextarea = document.getElementById('event-content');
        if (contentDisplay && contentTextarea) {
            contentTextarea.value = '';
            contentDisplay.style.display = 'block';
        }

        // Step 14: Auto-populate with current person if creating from person card
        if (this.currentPersonId && this.app.persons[this.currentPersonId]) {
            this.prePopulateCurrentPerson(type);
        }
    }

    prePopulateCurrentPerson(eventType) {
        const person = this.app.persons[this.currentPersonId];
        if (!person) return;

        // Determine role based on event type and person gender
        let targetRole = null;

        if (eventType === 'birth' || eventType === 'baptism') {
            // For birth, person becomes parent based on gender
            targetRole = person.gender === 'M' ? 'father' : person.gender === 'F' ? 'mother' : null;
        } else if (eventType === 'death' || eventType === 'burial') {
            // For death, person is deceased
            targetRole = 'deceased';
        } else if (eventType === 'marriage') {
            // For marriage, person is bride/groom based on gender
            targetRole = person.gender === 'M' ? 'groom' : person.gender === 'F' ? 'bride' : null;
        }

        if (targetRole) {
            // Use the existing selectExistingPerson method to populate
            this.selectExistingPerson(targetRole, this.currentPersonId);
            console.log(`Step 14: Auto-populated ${this.currentPersonId} as ${targetRole}`);
        }
    }

    buildParticipantsForm(type) {
        const container = document.getElementById('participants-container');
        container.innerHTML = '';

        let html = '<div style="margin-top: 20px; margin-bottom: 20px;"><h3>Participants</h3></div>';

        if (type === 'birth' || type === 'baptism') {
            html += this.buildPersonFields('child', 'Child', ['first_name', 'last_name', 'gender']);
            html += this.buildPersonFields('father', 'Father', ['first_name', 'last_name', 'maiden_name', 'age', 'occupation'], 'M');
            html += this.buildParentFields('father');
            html += this.buildPersonFields('mother', 'Mother', ['first_name', 'last_name', 'maiden_name', 'age', 'occupation'], 'F');
            html += this.buildParentFields('mother');
            html += this.buildPersonFields('witness_1', 'Witness 1', ['first_name', 'last_name', 'age', 'occupation', 'gender']);
            html += this.buildPersonFields('witness_2', 'Witness 2', ['first_name', 'last_name', 'age', 'occupation', 'gender']);
            html += this.buildPersonFields('godparent_1', 'Godparent 1', ['first_name', 'last_name', 'gender']);
            html += this.buildPersonFields('godparent_2', 'Godparent 2', ['first_name', 'last_name', 'gender']);
        } else if (type === 'marriage') {
            html += this.buildPersonFields('groom', 'Husband/Groom', ['first_name', 'last_name', 'maiden_name', 'age', 'occupation'], 'M');
            html += this.buildParentFields('groom');
            html += this.buildPersonFields('bride', 'Wife/Bride', ['first_name', 'last_name', 'maiden_name', 'age', 'occupation'], 'F');
            html += this.buildParentFields('bride');
            html += this.buildPersonFields('witness_1', 'Witness 1', ['first_name', 'last_name', 'age', 'occupation', 'gender']);
            html += this.buildPersonFields('witness_2', 'Witness 2', ['first_name', 'last_name', 'age', 'occupation', 'gender']);
        } else if (type === 'death' || type === 'burial') {
            html += this.buildPersonFields('deceased', 'Deceased', ['first_name', 'last_name', 'maiden_name', 'age', 'occupation', 'gender']);
            html += this.buildParentFields('deceased');
            html += this.buildPersonFields('witness_1', 'Witness 1', ['first_name', 'last_name', 'age', 'occupation', 'gender']);
            html += this.buildPersonFields('witness_2', 'Witness 2', ['first_name', 'last_name', 'age', 'occupation', 'gender']);
            html += this.buildPersonFields('witness_3', 'Witness 3', ['first_name', 'last_name', 'age', 'occupation', 'gender']);
        }

        container.innerHTML = html;
    }

    buildPersonFields(role, label, fields, defaultGender = null) {
        let html = `<div class="participant-section" data-role="${role}">
            <div style="background: #f0f4ff; padding: 12px; border-radius: 6px; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <h4 style="margin: 0; color: #667eea;">${label}</h4>
                    <button type="button" class="btn-secondary" style="padding: 4px 8px; font-size: 0.8rem;"
                            onclick="eventEditor.lookupPerson('${role}')">🔍 Lookup Person</button>
                </div>
                <input type="hidden" id="${role}_person_id" value="">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">`;

        fields.forEach(field => {
            if (field === 'first_name') {
                html += `<div><input type="text" id="${role}_first_name" placeholder="First Name" class="person-lookup-trigger" data-role="${role}"></div>`;
            } else if (field === 'last_name') {
                html += `<div><input type="text" id="${role}_last_name" placeholder="Last Name" class="person-lookup-trigger" data-role="${role}"></div>`;
            } else if (field === 'maiden_name') {
                html += `<div><input type="text" id="${role}_maiden_name" placeholder="Maiden Name"></div>`;
            } else if (field === 'age') {
                html += `<div><input type="number" id="${role}_age" placeholder="Age" min="0" max="150"></div>`;
            } else if (field === 'occupation') {
                html += `<div><input type="text" id="${role}_occupation" placeholder="Occupation"></div>`;
            } else if (field === 'gender') {
                html += `<div><select id="${role}_gender">
                    <option value="">Gender</option>
                    <option value="M" ${defaultGender === 'M' ? 'selected' : ''}>Male</option>
                    <option value="F" ${defaultGender === 'F' ? 'selected' : ''}>Female</option>
                </select></div>`;
            }
        });

        html += `</div>
                <div id="${role}_lookup_results" style="margin-top: 10px;"></div>
            </div>
        </div>`;

        return html;
    }

    buildParentFields(childRole) {
        const motherRole = `${childRole}_parent_mother`;
        const fatherRole = `${childRole}_parent_father`;

        return `<div style="padding-left: 20px; margin-bottom: 10px;">
            <div style="font-size: 0.9rem; font-weight: 500; margin-bottom: 8px; color: #666;">Parents of ${childRole}:</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div style="background: #f9f9f9; padding: 10px; border-radius: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <strong style="font-size: 0.85rem;">Mother</strong>
                        <button type="button" class="btn-secondary" style="padding: 2px 6px; font-size: 0.7rem;"
                                onclick="eventEditor.lookupPerson('${motherRole}')">🔍 Lookup</button>
                    </div>
                    <input type="hidden" id="${motherRole}_person_id" value="">
                    <input type="text" id="${motherRole}_first_name" placeholder="Mother's First Name" style="margin-bottom: 5px;" class="person-lookup-trigger" data-role="${motherRole}">
                    <input type="text" id="${motherRole}_last_name" placeholder="Mother's Last Name" style="margin-bottom: 5px;" class="person-lookup-trigger" data-role="${motherRole}">
                    <input type="text" id="${motherRole}_maiden_name" placeholder="Mother's Maiden Name">
                    <div id="${motherRole}_lookup_results" style="margin-top: 8px;"></div>
                </div>
                <div style="background: #f9f9f9; padding: 10px; border-radius: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <strong style="font-size: 0.85rem;">Father</strong>
                        <button type="button" class="btn-secondary" style="padding: 2px 6px; font-size: 0.7rem;"
                                onclick="eventEditor.lookupPerson('${fatherRole}')">🔍 Lookup</button>
                    </div>
                    <input type="hidden" id="${fatherRole}_person_id" value="">
                    <input type="text" id="${fatherRole}_first_name" placeholder="Father's First Name" style="margin-bottom: 5px;" class="person-lookup-trigger" data-role="${fatherRole}">
                    <input type="text" id="${fatherRole}_last_name" placeholder="Father's Last Name" style="margin-bottom: 5px;" class="person-lookup-trigger" data-role="${fatherRole}">
                    <input type="text" id="${fatherRole}_maiden_name" placeholder="Father's Maiden Name">
                    <div id="${fatherRole}_lookup_results" style="margin-top: 8px;"></div>
                </div>
            </div>
        </div>`;
    }

    lookupPerson(role) {
        const firstName = document.getElementById(`${role}_first_name`).value.trim();
        const lastName = document.getElementById(`${role}_last_name`).value.trim();

        if (!firstName || !lastName) {
            this.showNotification('Please enter first name and last name to search', 'warning');
            return;
        }

        // Search for matching persons
        const matches = [];
        Object.entries(this.app.persons).forEach(([id, person]) => {
            const personFirstName = (person.first_name || '').toLowerCase();
            const personLastName = (person.last_name || '').toLowerCase();

            if (personFirstName.includes(firstName.toLowerCase()) &&
                personLastName.includes(lastName.toLowerCase())) {
                matches.push({ id, person });
            }
        });

        this.displayLookupResults(role, matches);
    }

    displayLookupResults(role, matches) {
        const resultsContainer = document.getElementById(`${role}_lookup_results`);

        if (matches.length === 0) {
            resultsContainer.innerHTML = `<div style="padding: 10px; background: #fff3cd; border-radius: 4px; font-size: 0.9rem;">
                No matching persons found. A new person will be created.
            </div>`;
            return;
        }

        let html = `<div style="background: white; padding: 10px; border-radius: 4px; border: 1px solid #ddd;">
            <div style="font-weight: 600; margin-bottom: 8px;">Found ${matches.length} matching person(s):</div>`;

        matches.forEach(({ id, person }) => {
            const birthYear = this.app.extractYear(person.birth_date);
            const deathYear = this.app.extractYear(person.death_date);
            const years = birthYear || deathYear ? `(${birthYear || '?'} - ${deathYear || '?'})` : '';

            html += `<div style="padding: 8px; border: 1px solid #e0e0e0; border-radius: 4px; margin-bottom: 6px; cursor: pointer; transition: background 0.2s;"
                     onmouseover="this.style.background='#f0f4ff'" onmouseout="this.style.background='white'"
                     onclick="eventEditor.selectExistingPerson('${role}', '${id}')">
                <div style="font-weight: 500;">${this.app.getFullName(person)} ${years}</div>
                ${person.maiden_name ? `<div style="font-size: 0.85rem; color: #666;">Maiden: ${person.maiden_name}</div>` : ''}
                ${person.occupation ? `<div style="font-size: 0.85rem; color: #666;">Occupation: ${person.occupation}</div>` : ''}
                <div style="font-size: 0.85rem; color: #667eea;">Click to select</div>
            </div>`;
        });

        html += `<div style="margin-top: 8px; padding: 8px; background: #f8f9fa; border-radius: 4px; font-size: 0.85rem; color: #666;">
            Or leave unselected to create a new person with entered data.
        </div></div>`;

        resultsContainer.innerHTML = html;
    }

    selectExistingPerson(role, personId) {
        document.getElementById(`${role}_person_id`).value = personId;
        const person = this.app.persons[personId];

        // Fill in the form fields
        document.getElementById(`${role}_first_name`).value = person.first_name || '';
        document.getElementById(`${role}_last_name`).value = person.last_name || '';

        if (document.getElementById(`${role}_maiden_name`)) {
            document.getElementById(`${role}_maiden_name`).value = person.maiden_name || '';
        }
        if (document.getElementById(`${role}_occupation`)) {
            document.getElementById(`${role}_occupation`).value = person.occupation || '';
        }
        if (document.getElementById(`${role}_gender`)) {
            document.getElementById(`${role}_gender`).value = person.gender || '';
        }

        // Clear results and show selection
        const resultsContainer = document.getElementById(`${role}_lookup_results`);
        resultsContainer.innerHTML = `<div style="padding: 10px; background: #d4edda; border-radius: 4px; font-size: 0.9rem;">
            ✓ Selected: ${this.app.getFullName(person)} (${personId})
            <button type="button" style="margin-left: 10px; padding: 2px 6px; font-size: 0.8rem;"
                    onclick="eventEditor.clearPersonSelection('${role}')">Clear</button>
        </div>`;

        this.showNotification(`Selected ${this.app.getFullName(person)}`, 'success');
    }

    clearPersonSelection(role) {
        document.getElementById(`${role}_person_id`).value = '';
        document.getElementById(`${role}_lookup_results`).innerHTML = '';
    }

    loadEventParticipants(eventId) {
        // Get all participants for this event
        const participants = Object.values(this.app.event_participations)
            .filter(ep => ep.event_id === eventId);

        console.log(`Loading participants for event ${eventId}:`, participants.length);

        // Group participants by role
        const roleGroups = {};
        participants.forEach(ep => {
            const role = ep.role;
            if (!roleGroups[role]) {
                roleGroups[role] = [];
            }
            roleGroups[role].push(ep.person_id);
        });

        console.log('Role groups:', roleGroups);

        // Load single-role participants (child, father, mother, groom, bride, deceased)
        ['child', 'father', 'mother', 'groom', 'bride', 'deceased'].forEach(role => {
            if (roleGroups[role] && roleGroups[role].length > 0) {
                const personId = roleGroups[role][0];
                if (document.getElementById(`${role}_person_id`)) {
                    this.selectExistingPerson(role, personId);
                }
            }
        });

        // Load witnesses (witness_1, witness_2, witness_3)
        if (roleGroups['witness']) {
            console.log(`Loading ${roleGroups['witness'].length} witnesses`);
            roleGroups['witness'].forEach((personId, index) => {
                const slotRole = `witness_${index + 1}`;
                const field = document.getElementById(`${slotRole}_person_id`);
                console.log(`  Witness ${index + 1}: ${personId}, field exists: ${!!field}`);
                if (field) {
                    this.selectExistingPerson(slotRole, personId);
                }
            });
        }

        // Load godparents (godparent_1, godparent_2)
        if (roleGroups['godparent']) {
            roleGroups['godparent'].forEach((personId, index) => {
                const slotRole = `godparent_${index + 1}`;
                if (document.getElementById(`${slotRole}_person_id`)) {
                    this.selectExistingPerson(slotRole, personId);
                }
            });
        }

        // Step 5: Pre-populate parent fields for groom/bride/deceased if they exist
        const event = this.app.events[eventId];
        if (event && (event.type === 'marriage' || event.type === 'birth' || event.type === 'death')) {
            // Find parents for main participants
            ['groom', 'bride', 'father', 'mother', 'deceased'].forEach(mainRole => {
                if (roleGroups[mainRole] && roleGroups[mainRole].length > 0) {
                    const personId = roleGroups[mainRole][0];
                    const parents = this.findParents(personId);

                    if (parents.father) {
                        const fatherRole = `${mainRole}_parent_father`;
                        if (document.getElementById(`${fatherRole}_person_id`)) {
                            this.selectExistingPerson(fatherRole, parents.father);
                        }
                    }

                    if (parents.mother) {
                        const motherRole = `${mainRole}_parent_mother`;
                        if (document.getElementById(`${motherRole}_person_id`)) {
                            this.selectExistingPerson(motherRole, parents.mother);
                        }
                    }
                }
            });
        }
    }

    findParents(personId) {
        // Find parents by looking for birth events where this person is the child
        const parents = { father: null, mother: null };

        for (const ep of Object.values(this.app.event_participations)) {
            if (ep.person_id === personId && ep.role === 'child') {
                const event = this.app.events[ep.event_id];
                if (event && event.type === 'birth') {
                    // Find parents in this birth event
                    const eventParticipants = Object.values(this.app.event_participations)
                        .filter(e => e.event_id === ep.event_id);

                    eventParticipants.forEach(participant => {
                        if (participant.role === 'father') {
                            parents.father = participant.person_id;
                        } else if (participant.role === 'mother') {
                            parents.mother = participant.person_id;
                        }
                    });

                    break; // Found the birth event, stop searching
                }
            }
        }

        return parents;
    }

    async saveEvent() {
        // Collect event data
        const eventData = {
            type: this.currentEventType,
            date: {
                year: parseInt(document.getElementById('event-year').value) || null,
                month: parseInt(document.getElementById('event-month').value) || null,
                day: parseInt(document.getElementById('event-day').value) || null
            },
            place_name: document.getElementById('event-place').value.trim(),
            house_number: document.getElementById('event-house-number').value.trim(),
            tags: document.getElementById('event-tags').value.split(',').map(t => t.trim()).filter(Boolean),
            links: document.getElementById('event-links').value.split(',').map(l => l.trim()).filter(Boolean),
            notes: document.getElementById('event-notes').value.trim(),
            content: document.getElementById('event-content')?.value.trim() || null,
            participants: []
        };

        // Collect participants
        const participantSections = document.querySelectorAll('.participant-section');
        participantSections.forEach(section => {
            const role = section.dataset.role;
            const personId = document.getElementById(`${role}_person_id`).value;
            const firstName = document.getElementById(`${role}_first_name`)?.value.trim() || '';
            const lastName = document.getElementById(`${role}_last_name`)?.value.trim() || '';

            // Only include if we have an existing person OR both first and last name
            if (personId || (firstName && lastName)) {
                const participantData = {
                    role: this.mapRoleToEventParticipation(role),
                    existing_person_id: personId || null,
                    first_name: firstName,
                    last_name: lastName
                };

                // Add optional fields if they exist
                ['maiden_name', 'occupation', 'gender'].forEach(field => {
                    const element = document.getElementById(`${role}_${field}`);
                    if (element && element.value) {
                        participantData[field] = element.value;
                    }
                });

                // Handle age - calculate birth_date if age is provided
                const ageElement = document.getElementById(`${role}_age`);
                if (ageElement && ageElement.value) {
                    const age = parseInt(ageElement.value);
                    participantData.age = age;

                    // Calculate birth year from age and event year
                    // Only do this for NEW persons (not existing ones)
                    if (!personId && eventData.date.year) {
                        const birthYear = eventData.date.year - age;
                        participantData.calculated_birth_year = birthYear;
                    }
                }

                // Add parent data if exists
                ['mother', 'father'].forEach(parentType => {
                    const parentPersonId = document.getElementById(`${role}_parent_${parentType}_person_id`)?.value;
                    const parentFirstName = document.getElementById(`${role}_parent_${parentType}_first_name`)?.value.trim();
                    const parentLastName = document.getElementById(`${role}_parent_${parentType}_last_name`)?.value.trim();
                    if (parentPersonId || parentFirstName || parentLastName) {
                        participantData[`parent_${parentType}`] = {
                            existing_person_id: parentPersonId || null,
                            first_name: parentFirstName,
                            last_name: parentLastName,
                            maiden_name: document.getElementById(`${role}_parent_${parentType}_maiden_name`)?.value.trim()
                        };
                    }
                });

                eventData.participants.push(participantData);
            }
        });

        try {
            const endpoint = this.editingEventId ? '/api/update-event' : '/api/add-event';
            const payload = this.editingEventId ?
                { event_id: this.editingEventId, ...eventData } :
                eventData;

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification('Event saved successfully!', 'success');

                // Small delay to ensure server has written the file
                await new Promise(resolve => setTimeout(resolve, 100));

                // Reload data
                await this.app.loadData();

                // Recreate network to show new persons
                this.app.createNetwork();

                // Update statistics
                this.app.updateStats();

                // Refresh person details if viewing
                if (this.currentPersonId) {
                    this.app.showPersonDetails(this.currentPersonId);
                }

                // If new persons were created, show notification about them
                if (result.new_persons && result.new_persons.length > 0) {
                    const names = result.new_persons.map(p => `${p.first_name} ${p.last_name}`).join(', ');
                    this.showNotification(`Created ${result.new_persons.length} new person(s): ${names}`, 'success');

                    // Focus on the first new person in the network
                    const firstNewPersonId = result.new_persons[0].id;
                    setTimeout(() => {
                        this.app.network.selectNodes([firstNewPersonId]);
                        this.app.network.focus(firstNewPersonId, {
                            scale: 1.5,
                            animation: {
                                duration: 1000,
                                easingFunction: 'easeInOutQuad'
                            }
                        });
                    }, 500);
                }

                // Fit network to show everything
                setTimeout(() => {
                    this.app.network.fit({
                        animation: {
                            duration: 1000,
                            easingFunction: 'easeInOutQuad'
                        }
                    });
                }, 100);

                this.closeModal();
            } else {
                this.showNotification(`Error: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error saving event:', error);
            this.showNotification('Failed to save event. Check console for details.', 'error');
        }
    }

    mapRoleToEventParticipation(role) {
        const roleMap = {
            'child': 'child',
            'father': 'father',
            'mother': 'mother',
            'groom': 'groom',
            'bride': 'bride',
            'deceased': 'deceased',
            'witness_1': 'witness',
            'witness_2': 'witness',
            'witness_3': 'witness',
            'godparent_1': 'godparent',
            'godparent_2': 'godparent'
        };
        return roleMap[role] || role;
    }

    closeModal() {
        document.getElementById('event-editor-modal').style.display = 'none';
        this.currentEventType = null;
        this.currentPersonId = null;
        this.editingEventId = null;
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => notification.classList.add('show'), 10);
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Initialize event editor when app is ready
let eventEditor;
window.addEventListener('load', () => {
    setTimeout(() => {
        if (window.app) {
            eventEditor = new EventEditor(window.app);
            console.log('Event Editor initialized');
        }
    }, 1000);
});
