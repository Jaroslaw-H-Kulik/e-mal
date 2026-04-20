// Event Editor - Add and Edit Events

class EventEditor {
    constructor(app) {
        this.app = app;
        this.currentEventType = null;
        this.currentPersonId = null;
        this.editingEventId = null;
        this.onCloseCallback = null;
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
                            <div style="display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;">
                                <button class="btn-primary" onclick="eventEditor.selectEventType('birth')">Birth/Baptism</button>
                                <button class="btn-primary" onclick="eventEditor.selectEventType('marriage')">Marriage</button>
                                <button class="btn-primary" onclick="eventEditor.selectEventType('death')">Death</button>
                                <button class="btn-primary" onclick="eventEditor.selectEventType('generic')">Generic</button>
                                <button class="btn-primary" onclick="eventEditor.selectEventType('global')">Global</button>
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

    openAddGlobalEventModal() {
        this.currentPersonId = null;
        this.editingEventId = null;
        document.getElementById('event-editor-title').textContent = 'Add Global Event';
        document.getElementById('event-type-selection').style.display = 'none';
        document.getElementById('event-form-container').style.display = 'none';
        document.getElementById('event-form').reset();
        document.getElementById('event-editor-modal').style.display = 'block';
        this.selectEventType('global');
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

        // Step 47: Populate title field for generic events
        if (event.type === 'generic') {
            const titleField = document.getElementById('event-generic-title');
            if (titleField) titleField.value = event.title || '';
        }
        // Step 56.2: Populate title field for global events
        if (event.type === 'global') {
            const titleField = document.getElementById('event-global-title');
            if (titleField) titleField.value = event.title || '';
        }

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
        } else if (eventType === 'generic') {
            targetRole = 'participant_1';
        }

        if (targetRole) {
            // Use the existing selectExistingPerson method to populate
            this.selectExistingPerson(targetRole, this.currentPersonId);
            console.log(`Step 14: Auto-populated ${this.currentPersonId} as ${targetRole}`);
        }

        // Step 44: For birth events, also prepopulate the spouse as the other parent
        if ((eventType === 'birth' || eventType === 'baptism') && targetRole) {
            const spouseRole = targetRole === 'father' ? 'mother' : 'father';
            const family = this.app.getFamily(this.currentPersonId);
            if (family.spouses.length > 0) {
                // Pick the most recently married spouse
                const mostRecentSpouse = family.spouses.reduce((best, s) => {
                    const year = this.app.events[s.eventId]?.date?.year || 0;
                    const bestYear = this.app.events[best.eventId]?.date?.year || 0;
                    return year > bestYear ? s : best;
                });
                this.selectExistingPerson(spouseRole, mostRecentSpouse.id);
            }
        }

        // Step 41: Pre-populate place from person's birth event for marriage/death events
        if (eventType === 'marriage' || eventType === 'death' || eventType === 'burial') {
            const placeField = document.getElementById('event-place');
            if (placeField && !placeField.value) {
                // Find birth event where this person is the child
                const birthEp = Object.values(this.app.event_participations).find(ep =>
                    ep.person_id === this.currentPersonId && ep.role === 'child'
                );
                if (birthEp) {
                    const birthEvent = this.app.events[birthEp.event_id];
                    if (birthEvent?.place_id) {
                        const place = this.app.places[birthEvent.place_id];
                        if (place?.name) {
                            placeField.value = place.name;
                            // Step 54.1: Do not prepopulate house number
                        }
                    }
                }
            }
        }

        // Step 54: Prepopulate child's last name from father's last name in birth events
        if (eventType === 'birth' || eventType === 'baptism') {
            const fatherLastNameEl = document.getElementById('father_last_name');
            const childLastNameEl = document.getElementById('child_last_name');
            if (fatherLastNameEl && childLastNameEl && fatherLastNameEl.value && !childLastNameEl.value) {
                childLastNameEl.value = fatherLastNameEl.value;
            }
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
        } else if (type === 'generic') {
            html = `<div style="margin-bottom: 15px;">
                <div class="form-group">
                    <label style="font-weight: 600;">Event Title *</label>
                    <input type="text" id="event-generic-title" placeholder="e.g., Land sale, Court record..." style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box;">
                </div>
            </div>
            <div style="margin-top: 20px; margin-bottom: 20px;"><h3>Participants</h3></div>`;
            html += this.buildPersonFields('participant_1', 'Participant 1', ['first_name', 'last_name', 'gender', 'age', 'occupation']);
            html += this.buildPersonFields('participant_2', 'Participant 2', ['first_name', 'last_name', 'gender', 'age', 'occupation']);
            html += this.buildPersonFields('participant_3', 'Participant 3', ['first_name', 'last_name', 'gender', 'age', 'occupation']);
        } else if (type === 'global') {
            html = `<div style="margin-bottom: 15px;">
                <div class="form-group">
                    <label style="font-weight: 600;">Event Title *</label>
                    <input type="text" id="event-global-title" placeholder="e.g., War, Famine, Epidemic..." style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box;">
                </div>
                <div style="margin-top: 8px; padding: 8px 12px; background: #fff3cd; border-radius: 4px; font-size: 0.88rem; color: #856404;">
                    🌍 Global event — visible in event list for every person in the model
                </div>
            </div>`;
        }

        container.innerHTML = html;

        // Step 53: Auto-set gender from Polish name on blur for child in birth events
        if (type === 'birth' || type === 'baptism') {
            const childNameInput = document.getElementById('child_first_name');
            const childGenderField = document.getElementById('child_gender');
            if (childNameInput && childGenderField) {
                childNameInput.addEventListener('blur', () => {
                    const name = childNameInput.value.trim().toLowerCase();
                    if (!name) return;
                    const MALE_NAMES_ENDING_A = ['barnaba', 'bonawentura', 'kuba', 'sasza', 'jarema', 'seba'];
                    if (MALE_NAMES_ENDING_A.includes(name)) {
                        childGenderField.value = 'M';
                    } else if (name.endsWith('a')) {
                        childGenderField.value = 'F';
                    } else {
                        childGenderField.value = 'M';
                    }
                });
            }
        }
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
            const personMaidenName = (person.maiden_name || '').toLowerCase();

            if (personFirstName.includes(firstName.toLowerCase()) &&
                (personLastName.includes(lastName.toLowerCase()) || personMaidenName.includes(lastName.toLowerCase()))) {
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
            const birthYear = this.app.extractYear(this.app.getPersonBirthDate(id));
            const deathYear = this.app.extractYear(this.app.getPersonDeathDate(id));
            const years = birthYear || deathYear ? `(${birthYear || '?'} - ${deathYear || '?'})` : '';
            const family = this.app.getFamily(id);
            const spouseNames = family.spouses.map(s => {
                const sp = this.app.persons[s.id];
                return sp ? this.app.getFullName(sp) : s.id;
            }).join(', ');

            html += `<div style="padding: 8px; border: 1px solid #e0e0e0; border-radius: 4px; margin-bottom: 6px; cursor: pointer; transition: background 0.2s;"
                     onmouseover="this.style.background='#f0f4ff'" onmouseout="this.style.background='white'"
                     onclick="eventEditor.selectExistingPerson('${role}', '${id}')">
                <div style="font-weight: 500;">${this.app.getFullName(person)} ${years}</div>
                ${person.maiden_name ? `<div style="font-size: 0.85rem; color: #666;">Maiden: ${person.maiden_name}</div>` : ''}
                ${person.occupation ? `<div style="font-size: 0.85rem; color: #666;">Occupation: ${person.occupation}</div>` : ''}
                ${spouseNames ? `<div style="font-size: 0.85rem; color: #666;">Spouse(s): ${spouseNames}</div>` : ''}
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

        // Load generic event participants (participant_1, participant_2, participant_3)
        if (roleGroups['participant']) {
            roleGroups['participant'].forEach((personId, index) => {
                const slotRole = `participant_${index + 1}`;
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
            title: this.currentEventType === 'generic'
                ? (document.getElementById('event-generic-title')?.value.trim() || null)
                : this.currentEventType === 'global'
                    ? (document.getElementById('event-global-title')?.value.trim() || null)
                    : null,
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

        // Step 45: Capture parent IDs/names before save for marriage event check
        const isBirthEvent = (this.currentEventType === 'birth' || this.currentEventType === 'baptism');
        const preSaveFatherId = document.getElementById('father_person_id')?.value || null;
        const preSaveMotherId = document.getElementById('mother_person_id')?.value || null;
        const preSaveFatherName = {
            first: document.getElementById('father_first_name')?.value.trim() || '',
            last: document.getElementById('father_last_name')?.value.trim() || ''
        };
        const preSaveMotherName = {
            first: document.getElementById('mother_first_name')?.value.trim() || '',
            last: document.getElementById('mother_last_name')?.value.trim() || ''
        };

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

                const hasNewPersons = result.new_persons && result.new_persons.length > 0;

                if (this.editingEventId && !hasNewPersons) {
                    // Fast path for updates: patch in-memory state, no network round-trip
                    this.app.events[this.editingEventId] = result.event;

                    // Remove old participations for this event and add new ones
                    Object.keys(this.app.event_participations).forEach(epId => {
                        if (this.app.event_participations[epId].event_id === this.editingEventId) {
                            delete this.app.event_participations[epId];
                        }
                    });
                    if (result.event_participations) {
                        Object.assign(this.app.event_participations, result.event_participations);
                    }

                    // Patch modified persons (e.g. maiden_name updated for existing participants)
                    if (result.modified_persons && result.modified_persons.length > 0) {
                        result.modified_persons.forEach(p => {
                            this.app.persons[p.id] = p;
                        });
                    }

                    // Rebuild indices and caches
                    this.app.buildIndices();
                    if (this.app.familyCache) this.app.familyCache.clear();

                    // Immediately refresh person card
                    if (this.currentPersonId) {
                        this.app.showPersonDetails(this.currentPersonId);
                    }
                } else {
                    // Slow path for new events or when new persons were created
                    await new Promise(resolve => setTimeout(resolve, 100));
                    await this.app.loadData();
                    this.app.createNetwork();
                    this.app.updateStats();

                    if (this.currentPersonId) {
                        this.app.showPersonDetails(this.currentPersonId);
                    }

                    // Step 45: Auto-create marriage event for parents if missing
                    if (isBirthEvent) {
                        await this.maybeCreateMarriageForParents(
                            preSaveFatherId, preSaveFatherName,
                            preSaveMotherId, preSaveMotherName,
                            result.new_persons || []
                        );
                    }

                    if (hasNewPersons) {
                        const names = result.new_persons.map(p => `${p.first_name} ${p.last_name}`).join(', ');
                        this.showNotification(`Created ${result.new_persons.length} new person(s): ${names}`, 'success');

                        const firstNewPersonId = result.new_persons[0].id;
                        setTimeout(() => {
                            this.app.network.selectNodes([firstNewPersonId]);
                            this.app.network.focus(firstNewPersonId, {
                                scale: 1.5,
                                animation: { duration: 1000, easingFunction: 'easeInOutQuad' }
                            });
                        }, 500);
                    }
                }

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
            'godparent_2': 'godparent',
            'participant_1': 'participant',
            'participant_2': 'participant',
            'participant_3': 'participant'
        };
        return roleMap[role] || role;
    }

    closeModal() {
        document.getElementById('event-editor-modal').style.display = 'none';
        this.currentEventType = null;
        this.currentPersonId = null;
        this.editingEventId = null;

        // Step 36: Fire sequential import callback if set
        if (this.onCloseCallback) {
            const cb = this.onCloseCallback;
            this.onCloseCallback = null;
            cb();
        }
    }

    openBirthFromGeneteka(record, personId, current, total) {
        // Step 36: Open birth event creation modal pre-populated with Geneteka record
        this.currentPersonId = personId;
        this.editingEventId = null;
        this.currentEventType = 'birth';

        document.getElementById('event-editor-title').textContent =
            `Geneteka Import (${current}/${total}) — Birth ${record.rok || '?'}: ${record.imie_dziecka} ${record.nazwisko}`;
        document.getElementById('event-type-selection').style.display = 'none';
        document.getElementById('event-form-container').style.display = 'block';
        document.getElementById('event-form').reset();

        this.buildParticipantsForm('birth');

        document.getElementById('event-editor-modal').style.display = 'block';

        setTimeout(() => this.populateFromGenetikaRecord(record, personId), 50);
    }

    populateFromGenetikaRecord(record, personId) {
        // Year / place
        if (record.rok) document.getElementById('event-year').value = record.rok;
        if (record.miejscowosc) document.getElementById('event-place').value = record.miejscowosc;

        // Child
        if (record.imie_dziecka) document.getElementById('child_first_name').value = record.imie_dziecka;
        if (record.nazwisko) document.getElementById('child_last_name').value = record.nazwisko;

        // Father (last name = child's surname)
        if (record.imie_ojca) document.getElementById('father_first_name').value = record.imie_ojca;
        if (record.nazwisko) document.getElementById('father_last_name').value = record.nazwisko;

        // Mother (last name = child's surname, maiden name from nazwisko_matki)
        if (record.imie_matki) document.getElementById('mother_first_name').value = record.imie_matki;
        if (record.nazwisko) document.getElementById('mother_last_name').value = record.nazwisko;
        if (record.nazwisko_matki) {
            const maidenEl = document.getElementById('mother_maiden_name');
            if (maidenEl) maidenEl.value = record.nazwisko_matki;
        }

        // Pre-select the importing person in their role first, then overwrite with Geneteka data
        const person = this.app.persons[personId];
        if (person) {
            const isBirthLookup = this.app.genetikaImportType === 'birth';
            const role = isBirthLookup ? 'child'
                : (person.gender === 'M' ? 'father' : 'mother');
            this.selectExistingPerson(role, personId);
        }

        // Re-apply Geneteka data so it takes precedence over model (e.g. mother maiden name)
        if (record.imie_dziecka) document.getElementById('child_first_name').value = record.imie_dziecka;
        if (record.nazwisko) document.getElementById('child_last_name').value = record.nazwisko;
        if (record.imie_ojca) document.getElementById('father_first_name').value = record.imie_ojca;
        if (record.nazwisko) document.getElementById('father_last_name').value = record.nazwisko;
        if (record.imie_matki) document.getElementById('mother_first_name').value = record.imie_matki;
        if (record.nazwisko) document.getElementById('mother_last_name').value = record.nazwisko;
        if (record.nazwisko_matki) {
            const maidenEl = document.getElementById('mother_maiden_name');
            if (maidenEl) maidenEl.value = record.nazwisko_matki;
        }

        // Build content / summary
        const parts = [
            `Rok: ${record.rok}  Akt: ${record.akt}`,
            `Dziecko: ${record.imie_dziecka} ${record.nazwisko}`,
            `Ojciec: ${record.imie_ojca} ${record.nazwisko}`,
            `Matka: ${record.imie_matki} ${record.nazwisko_matki ? record.nazwisko_matki + ' /' : ''} ${record.nazwisko}`,
            `Parafia: ${record.parafia}  Miejscowość: ${record.miejscowosc}`,
        ];
        if (record.uwagi) parts.push(`Uwagi: ${record.uwagi}`);
        if (record.links && record.links.length > 0) parts.push(`Linki: ${record.links.join(', ')}`);

        const contentDisplay = document.getElementById('event-content-display');
        const contentTextarea = document.getElementById('event-content');
        if (contentDisplay && contentTextarea) {
            contentTextarea.value = parts.join('\n');
            contentDisplay.style.display = 'block';
        }
    }

    // Step 38: Marriage from Geneteka ─────────────────────────────────────────
    openMarriageFromGeneteka(record, personId, current, total) {
        this.currentPersonId = personId;
        this.editingEventId = null;
        this.currentEventType = 'marriage';

        document.getElementById('event-editor-title').textContent =
            `Geneteka Import (${current}/${total}) — Marriage ${record.rok || '?'}: ${record.imie_pana} ${record.nazwisko_pana} & ${record.imie_pani} ${record.nazwisko_pani}`;
        document.getElementById('event-type-selection').style.display = 'none';
        document.getElementById('event-form-container').style.display = 'block';
        document.getElementById('event-form').reset();

        this.buildParticipantsForm('marriage');
        document.getElementById('event-editor-modal').style.display = 'block';

        setTimeout(() => this.populateFromGenetikaMarriageRecord(record, personId), 50);
    }

    populateFromGenetikaMarriageRecord(record, personId) {
        if (record.rok) document.getElementById('event-year').value = record.rok;
        if (record.miejscowosc) document.getElementById('event-place').value = record.miejscowosc;

        const setField = (id, val) => { const el = document.getElementById(id); if (el && val) el.value = val; };

        // Link the importing person first (sets person_id + model name fields)
        const person = this.app.persons[personId];
        if (person) {
            const role = person.gender === 'M' ? 'groom' : 'bride';
            this.selectExistingPerson(role, personId);
        }

        // Now overwrite all fields from Geneteka (takes precedence, e.g. bride maiden_name)
        // Groom
        setField('groom_first_name', record.imie_pana);
        setField('groom_last_name', record.nazwisko_pana);

        // Groom's parents
        const rp = record.rodzice_pana_parsed || {};
        setField('groom_parent_father_first_name', rp.father_name);
        setField('groom_parent_father_last_name', record.nazwisko_pana);
        setField('groom_parent_mother_first_name', rp.mother_name);
        setField('groom_parent_mother_maiden_name', rp.mother_maiden);
        setField('groom_parent_mother_last_name', record.nazwisko_pana);

        // Bride
        setField('bride_first_name', record.imie_pani);
        setField('bride_last_name', record.nazwisko_pani);
        setField('bride_maiden_name', record.nazwisko_pani); // bride's surname IS her maiden name

        // Bride's parents
        const bp = record.rodzice_pani_parsed || {};
        setField('bride_parent_father_first_name', bp.father_name);
        setField('bride_parent_father_last_name', record.nazwisko_pani);
        setField('bride_parent_mother_first_name', bp.mother_name);
        setField('bride_parent_mother_maiden_name', bp.mother_maiden);
        setField('bride_parent_mother_last_name', record.nazwisko_pani);

        // Content / summary
        const parts = [
            `Rok: ${record.rok}  Akt: ${record.akt}`,
            `Pan: ${record.imie_pana} ${record.nazwisko_pana}  Rodzice: ${record.rodzice_pana || '—'}`,
            `Pani: ${record.imie_pani} ${record.nazwisko_pani}  Rodzice: ${record.rodzice_pani || '—'}`,
            `Miejscowość: ${record.miejscowosc}`,
        ];
        if (record.uwagi) parts.push(`Uwagi: ${record.uwagi}`);
        if (record.links && record.links.length > 0) parts.push(`Linki: ${record.links.join(', ')}`);

        const contentDisplay = document.getElementById('event-content-display');
        const contentTextarea = document.getElementById('event-content');
        if (contentDisplay && contentTextarea) {
            contentTextarea.value = parts.join('\n');
            contentDisplay.style.display = 'block';
        }
    }

    // Step 38: Death from Geneteka ────────────────────────────────────────────
    openDeathFromGeneteka(record, personId, current, total) {
        this.currentPersonId = personId;
        this.editingEventId = null;
        this.currentEventType = 'death';

        document.getElementById('event-editor-title').textContent =
            `Geneteka Import (${current}/${total}) — Death ${record.rok || '?'}: ${record.imie} ${record.nazwisko}`;
        document.getElementById('event-type-selection').style.display = 'none';
        document.getElementById('event-form-container').style.display = 'block';
        document.getElementById('event-form').reset();

        this.buildParticipantsForm('death');
        document.getElementById('event-editor-modal').style.display = 'block';

        setTimeout(() => this.populateFromGenetikaDeathRecord(record, personId), 50);
    }

    populateFromGenetikaDeathRecord(record, personId) {
        const setField = (id, val) => { const el = document.getElementById(id); if (el && val) el.value = val; };

        if (record.rok) document.getElementById('event-year').value = record.rok;
        if (record.miejscowosc) document.getElementById('event-place').value = record.miejscowosc;

        // Deceased
        setField('deceased_first_name', record.imie);
        setField('deceased_last_name', record.nazwisko);

        // Deceased's parents
        setField('deceased_parent_father_first_name', record.imie_ojca);
        setField('deceased_parent_father_last_name', record.nazwisko);
        setField('deceased_parent_mother_first_name', record.imie_matki);
        setField('deceased_parent_mother_maiden_name', record.nazwisko_matki);
        setField('deceased_parent_mother_last_name', record.nazwisko);

        // Pre-select the importing person as deceased
        const person = this.app.persons[personId];
        if (person) {
            this.selectExistingPerson('deceased', personId);
        }

        // Content / summary
        const parts = [
            `Rok: ${record.rok}  Akt: ${record.akt}`,
            `Zmarły/a: ${record.imie} ${record.nazwisko}`,
            `Ojciec: ${record.imie_ojca || '—'}  Matka: ${record.imie_matki || '—'} ${record.nazwisko_matki ? '/ ' + record.nazwisko_matki : ''}`,
            `Miejscowość: ${record.miejscowosc}`,
        ];
        if (record.uwagi) parts.push(`Uwagi: ${record.uwagi}`);
        if (record.links && record.links.length > 0) parts.push(`Linki: ${record.links.join(', ')}`);

        const contentDisplay = document.getElementById('event-content-display');
        const contentTextarea = document.getElementById('event-content');
        if (contentDisplay && contentTextarea) {
            contentTextarea.value = parts.join('\n');
            contentDisplay.style.display = 'block';
        }
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

    // Step 45: Create marriage event for birth event parents if one doesn't exist yet
    async maybeCreateMarriageForParents(preFatherId, fatherName, preMotherId, motherName, newPersons) {
        const resolveId = (existingId, name) => {
            if (existingId) return existingId;
            if (!name.first || !name.last) return null;
            const found = newPersons.find(p =>
                p.first_name.toLowerCase() === name.first.toLowerCase() &&
                p.last_name.toLowerCase() === name.last.toLowerCase()
            );
            return found ? found.id : null;
        };

        const fatherId = resolveId(preFatherId, fatherName);
        const motherId = resolveId(preMotherId, motherName);
        if (!fatherId || !motherId) return;

        // Check if marriage already exists between them
        const fatherMarriageEvents = new Set();
        for (const ep of Object.values(this.app.event_participations)) {
            if (ep.person_id === fatherId && this.app.events[ep.event_id]?.type === 'marriage') {
                fatherMarriageEvents.add(ep.event_id);
            }
        }
        for (const ep of Object.values(this.app.event_participations)) {
            if (ep.person_id === motherId && fatherMarriageEvents.has(ep.event_id)) {
                return; // Already married
            }
        }

        // Create minimal marriage event
        const father = this.app.persons[fatherId];
        const mother = this.app.persons[motherId];
        const response = await fetch('/api/add-event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'marriage',
                date: { year: null, month: null, day: null },
                participants: [
                    { role: 'groom', existing_person_id: fatherId, first_name: father?.first_name || '', last_name: father?.last_name || '' },
                    { role: 'bride', existing_person_id: motherId, first_name: mother?.first_name || '', last_name: mother?.last_name || '' }
                ]
            })
        });

        const marriageResult = await response.json();
        if (marriageResult.success) {
            await this.app.loadData();
            this.showNotification('Created marriage event for parents', 'info');
        }
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
