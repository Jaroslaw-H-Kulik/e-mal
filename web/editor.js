// Genealogy Editor - Edit and Merge Persons

class GenealogyEditor {
    constructor(app) {
        this.app = app;
        this.editingPerson = null;
        this.mergingPersons = [];
        this.setupEditor();
    }

    setupEditor() {
        // Add modal HTML to page
        const modalHTML = `
            <!-- Edit Person Modal -->
            <div id="edit-modal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>Edit Person</h2>
                        <button class="close-modal" onclick="editor.closeEditModal()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <form id="edit-person-form">
                            <div class="form-group">
                                <label>Person ID</label>
                                <input type="text" id="edit-id" readonly>
                            </div>
                            <div class="form-group">
                                <label>Given Name *</label>
                                <input type="text" id="edit-given-name" required>
                            </div>
                            <div class="form-group">
                                <label>Surname *</label>
                                <input type="text" id="edit-surname" required>
                            </div>
                            <div class="form-group">
                                <label>Maiden Name</label>
                                <input type="text" id="edit-maiden-name" placeholder="Optional">
                            </div>
                            <div class="form-group">
                                <label>Gender</label>
                                <select id="edit-gender">
                                    <option value="M">Male (♂)</option>
                                    <option value="F">Female (♀)</option>
                                    <option value="U">Unknown</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Birth Year (estimate)</label>
                                <input type="number" id="edit-birth-year" min="1700" max="2000">
                            </div>
                            <div class="form-group">
                                <label>Death Year (estimate)</label>
                                <input type="number" id="edit-death-year" min="1700" max="2000">
                            </div>
                            <div class="form-group">
                                <label>Place of Birth</label>
                                <input type="text" id="edit-place-of-birth" placeholder="Settlement name" list="edit-place-suggestions">
                            </div>
                            <div class="form-group">
                                <label>Place of Death</label>
                                <input type="text" id="edit-place-of-death" placeholder="Settlement name" list="edit-place-suggestions">
                                <datalist id="edit-place-suggestions">
                                    <option value="Małyszyn">
                                    <option value="Tychów">
                                    <option value="Bór Iłżecki">
                                    <option value="Gaworzyna">
                                    <option value="Starosiedlice">
                                    <option value="Mirzec">
                                </datalist>
                            </div>
                            <div class="form-group">
                                <label>Occupations (comma-separated)</label>
                                <input type="text" id="edit-occupations" placeholder="e.g., młynarz, wyrobnik">
                            </div>
                            <div class="form-actions">
                                <button type="submit" class="btn-primary">Save Changes</button>
                                <button type="button" class="btn-secondary" onclick="editor.closeEditModal()">Cancel</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>

            <!-- Merge Modal -->
            <div id="merge-modal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>Merge Persons</h2>
                        <button class="close-modal" onclick="editor.closeMergeModal()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <p class="help-text">
                            Select two persons to merge. The first person will be kept, and the second will be merged into it.
                        </p>
                        <div class="merge-selection">
                            <div class="merge-person">
                                <h3>Keep This Person (Primary)</h3>
                                <div id="merge-person-1" class="person-card">
                                    <p class="empty-text">Click "Select" on a person to choose primary</p>
                                </div>
                            </div>
                            <div class="merge-arrow">→</div>
                            <div class="merge-person">
                                <h3>Merge Into Primary</h3>
                                <div id="merge-person-2" class="person-card">
                                    <p class="empty-text">Click "Select" on another person to merge</p>
                                </div>
                            </div>
                        </div>
                        <div class="form-actions">
                            <button type="button" class="btn-danger" onclick="editor.executeMerge()" id="merge-execute-btn" disabled>
                                Merge Persons
                            </button>
                            <button type="button" class="btn-secondary" onclick="editor.closeMergeModal()">Cancel</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Add edit form submit handler
        document.getElementById('edit-person-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.savePersonEdit();
        });

        // Step 46/53: Auto-set gender from Polish given name on blur
        const MALE_NAMES_ENDING_A = ['barnaba', 'bonawentura', 'kuba', 'sasza', 'jarema', 'seba'];
        const inferGenderFromPolishName = (name) => {
            if (!name) return null;
            const lower = name.trim().toLowerCase();
            if (MALE_NAMES_ENDING_A.includes(lower)) return 'M';
            if (lower.endsWith('a')) return 'F';
            return 'M';
        };

        document.getElementById('edit-given-name').addEventListener('blur', () => {
            const name = document.getElementById('edit-given-name').value.trim();
            if (!name) return;
            document.getElementById('edit-gender').value = inferGenderFromPolishName(name);
        });

        // Step 53: Same logic for Add Person modal
        document.getElementById('add-given-name').addEventListener('blur', () => {
            const name = document.getElementById('add-given-name').value.trim();
            if (!name) return;
            document.getElementById('add-gender').value = inferGenderFromPolishName(name);
        });
    }

    openEditModal(personId) {
        const person = this.app.persons[personId];
        if (!person) return;

        this.editingPerson = personId;

        // Fill form with all fields for THIS person
        document.getElementById('edit-id').value = personId;
        document.getElementById('edit-given-name').value = person.first_name || '';
        document.getElementById('edit-surname').value = person.last_name || '';
        document.getElementById('edit-maiden-name').value = person.maiden_name || '';
        document.getElementById('edit-gender').value = person.gender || 'U';

        // Clear place fields (using correct IDs from index.html)
        const placeBirthEl = document.getElementById('edit-place-birth');
        const placeDeathEl = document.getElementById('edit-place-death');
        if (placeBirthEl) placeBirthEl.value = '';
        if (placeDeathEl) placeDeathEl.value = '';

        document.getElementById('edit-occupations').value = person.occupation || '';
        // Step 56: Populate tags and notes
        document.getElementById('edit-tags').value = person.tags && person.tags.length > 0 ? person.tags.join(', ') : '';
        document.getElementById('edit-notes').value = person.notes || '';

        // Show modal
        document.getElementById('edit-modal').style.display = 'block';
    }

    closeEditModal() {
        document.getElementById('edit-modal').style.display = 'none';
        this.editingPerson = null;
    }

    async savePersonEdit(event) {
        if (event) event.preventDefault();

        const personId = this.editingPerson;
        const person = this.app.persons[personId];

        // Get place values
        const placeBirth = document.getElementById('edit-place-birth')?.value.trim() || null;
        const placeDeath = document.getElementById('edit-place-death')?.value.trim() || null;

        // Step 56: Parse tags from comma-separated input
        const tagsRaw = document.getElementById('edit-tags')?.value || '';
        const tags = tagsRaw.split(',').map(t => t.trim()).filter(t => t.length > 0);

        const updateData = {
            person_id: personId,
            first_name: document.getElementById('edit-given-name').value,
            last_name: document.getElementById('edit-surname').value,
            maiden_name: document.getElementById('edit-maiden-name').value || null,
            gender: document.getElementById('edit-gender').value,
            occupation: document.getElementById('edit-occupations').value || null,
            place_of_birth: placeBirth,
            place_of_death: placeDeath,
            tags: tags,
            notes: document.getElementById('edit-notes')?.value || null
        };

        console.log('Saving person with data:', updateData);

        try {
            // Step 9: Use new update endpoint that syncs to events
            const response = await fetch('/api/update-person', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updateData)
            });

            const result = await response.json();
            console.log('Server response:', result);

            if (result.success) {
                // Update local person data
                Object.assign(person, result.person);

                // Update network
                const birthYear = this.app.extractYear(this.app.getPersonBirthDate(personId));
                const deathYear = this.app.extractYear(this.app.getPersonDeathDate(personId));
                this.app.network.body.data.nodes.update({
                    id: personId,
                    label: `${this.app.getFullName(result.person)}\n(${birthYear || '?'}-${deathYear || '?'})`,
                    color: this.app.getPersonColor(result.person.gender)
                });

                // Reload data to get synced events
                await this.app.loadData();

                // Refresh person details
                this.app.showPersonDetails(personId);

                this.closeEditModal();

                // Show success message
                let message = 'Person updated successfully!';
                if (result.updated_events && result.updated_events.length > 0) {
                    message += ` (${result.updated_events.length} event(s) synced)`;
                }
                this.showNotification(message, 'success');
            } else {
                this.showNotification(`Error: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error updating person:', error);
            this.showNotification('Failed to update person', 'error');
        }
    }

    openMergeModal() {
        // Check if persons are already selected (from person details panel)
        if (this.mergingPersons.length === 0) {
            // No pre-selection, start fresh
            document.getElementById('merge-person-1').innerHTML = '<p class="empty-text">Click "Select" on a person to choose primary</p>';
            document.getElementById('merge-person-2').innerHTML = '<p class="empty-text">Click "Select" on another person to merge</p>';
            document.getElementById('merge-execute-btn').disabled = true;
        } else if (this.mergingPersons.length === 1) {
            // One person already selected, show it
            const person1 = this.app.persons[this.mergingPersons[0]];
            const cardHTML1 = `
                <div class="person-info">
                    <strong>${person1.given_name} ${person1.surname}</strong>
                    <div class="person-meta">
                        ${this.mergingPersons[0]} • ${person1.birth_year_estimate || '?'}-${person1.death_year_estimate || '?'}
                    </div>
                    ${person1.maiden_name ? `<div>Maiden: ${person1.maiden_name}</div>` : ''}
                </div>
                <button class="btn-small" onclick="editor.clearMergeSelection(1)">Clear</button>
            `;
            document.getElementById('merge-person-1').innerHTML = cardHTML1;
            document.getElementById('merge-person-2').innerHTML = '<p class="empty-text">Click "Select" on another person to merge</p>';
            document.getElementById('merge-execute-btn').disabled = true;
        } else if (this.mergingPersons.length === 2) {
            // Both persons already selected
            const person1 = this.app.persons[this.mergingPersons[0]];
            const person2 = this.app.persons[this.mergingPersons[1]];

            const cardHTML1 = `
                <div class="person-info">
                    <strong>${person1.given_name} ${person1.surname}</strong>
                    <div class="person-meta">
                        ${this.mergingPersons[0]} • ${person1.birth_year_estimate || '?'}-${person1.death_year_estimate || '?'}
                    </div>
                    ${person1.maiden_name ? `<div>Maiden: ${person1.maiden_name}</div>` : ''}
                </div>
                <button class="btn-small" onclick="editor.clearMergeSelection(1)">Clear</button>
            `;

            const cardHTML2 = `
                <div class="person-info">
                    <strong>${person2.given_name} ${person2.surname}</strong>
                    <div class="person-meta">
                        ${this.mergingPersons[1]} • ${person2.birth_year_estimate || '?'}-${person2.death_year_estimate || '?'}
                    </div>
                    ${person2.maiden_name ? `<div>Maiden: ${person2.maiden_name}</div>` : ''}
                </div>
                <button class="btn-small" onclick="editor.clearMergeSelection(2)">Clear</button>
            `;

            document.getElementById('merge-person-1').innerHTML = cardHTML1;
            document.getElementById('merge-person-2').innerHTML = cardHTML2;
            document.getElementById('merge-execute-btn').disabled = false;
        }

        document.getElementById('merge-modal').style.display = 'flex';
    }

    closeMergeModal() {
        document.getElementById('merge-modal').style.display = 'none';
        this.mergingPersons = [];
    }

    selectPersonForMerge(personId) {
        if (this.mergingPersons.length >= 2) {
            this.showNotification('Already selected 2 persons. Clear selection first.', 'warning');
            return;
        }

        if (this.mergingPersons.includes(personId)) {
            this.showNotification('Person already selected', 'warning');
            return;
        }

        this.mergingPersons.push(personId);
        const person = this.app.persons[personId];

        const cardHTML = `
            <div class="person-info">
                <strong>${person.first_name} ${person.last_name}</strong>
                <div class="person-meta">
                    ${personId} • ${this.app.extractYear(this.app.getPersonBirthDate(personId)) || '?'}-${this.app.extractYear(this.app.getPersonDeathDate(personId)) || '?'}
                </div>
                ${person.maiden_name ? `<div>Maiden: ${person.maiden_name}</div>` : ''}
            </div>
            <button class="btn-small" onclick="editor.clearMergeSelection(${this.mergingPersons.length})">Clear</button>
        `;

        // Show notification about selection
        if (this.mergingPersons.length === 1) {
            this.showNotification(`Selected ${person.first_name} ${person.last_name}. Select one more person to merge.`, 'info');
        } else if (this.mergingPersons.length === 2) {
            this.showNotification('Two persons selected! Opening merge dialog...', 'success');
        }

        // Update the merge modal if it's open
        const mergeModalOpen = document.getElementById('merge-modal').style.display === 'flex';

        if (mergeModalOpen) {
            // Modal is already open, update it
            if (this.mergingPersons.length === 1) {
                document.getElementById('merge-person-1').innerHTML = cardHTML;
            } else {
                document.getElementById('merge-person-2').innerHTML = cardHTML;
                document.getElementById('merge-execute-btn').disabled = false;
            }
        } else {
            // Modal not open, populate data for when it opens
            // If both persons selected, auto-open the modal
            if (this.mergingPersons.length === 2) {
                // Populate both slots before opening
                const person1 = this.app.persons[this.mergingPersons[0]];
                const cardHTML1 = `
                    <div class="person-info">
                        <strong>${person1.given_name} ${person1.surname}</strong>
                        <div class="person-meta">
                            ${this.mergingPersons[0]} • ${person1.birth_year_estimate || '?'}-${person1.death_year_estimate || '?'}
                        </div>
                        ${person1.maiden_name ? `<div>Maiden: ${person1.maiden_name}</div>` : ''}
                    </div>
                    <button class="btn-small" onclick="editor.clearMergeSelection(1)">Clear</button>
                `;

                document.getElementById('merge-person-1').innerHTML = cardHTML1;
                document.getElementById('merge-person-2').innerHTML = cardHTML;
                document.getElementById('merge-execute-btn').disabled = false;

                // Open the modal
                document.getElementById('merge-modal').style.display = 'flex';
            }
        }
    }

    clearMergeSelection(slot) {
        if (slot === 1) {
            this.mergingPersons[0] = null;
            document.getElementById('merge-person-1').innerHTML = '<p class="empty-text">Click "Select" on a person to choose primary</p>';
        } else {
            this.mergingPersons[1] = null;
            document.getElementById('merge-person-2').innerHTML = '<p class="empty-text">Click "Select" on another person to merge</p>';
        }
        this.mergingPersons = this.mergingPersons.filter(Boolean);
        document.getElementById('merge-execute-btn').disabled = this.mergingPersons.length < 2;
    }

    executeMerge() {
        if (this.mergingPersons.length !== 2) {
            this.showNotification('Please select exactly 2 persons', 'error');
            return;
        }

        const [keepId, mergeId] = this.mergingPersons;
        const keepPerson = this.app.persons[keepId];
        const mergePerson = this.app.persons[mergeId];

        if (!confirm(`Merge ${mergePerson.given_name} ${mergePerson.surname} (${mergeId}) into ${keepPerson.given_name} ${keepPerson.surname} (${keepId})?\n\nThis will update all relationships and events.`)) {
            return;
        }

        // Update all event participations
        Object.values(this.app.event_participations).forEach(ep => {
            if (ep.person_id === mergeId) {
                ep.person_id = keepId;
            }
        });

        // Remove merged person from network
        this.app.network.body.data.nodes.remove(mergeId);

        // Remove merged person from data
        delete this.app.persons[mergeId];

        // Clear search results (so removed person doesn't appear)
        const searchInput = document.getElementById('search-input');
        const searchResults = document.getElementById('search-results');
        if (searchInput.value.trim()) {
            // Re-run search to update results
            this.app.handleSearch();
        } else {
            // Just clear results
            searchResults.innerHTML = '';
        }

        // Auto-save updated data
        this.saveDataToServer();

        // Close modal
        this.closeMergeModal();

        // Refresh view
        this.app.showPersonDetails(keepId);
        this.app.network.selectNodes([keepId]);

        this.showNotification(`Successfully merged ${mergeId} into ${keepId}`, 'success');
    }

    async saveDataToServer() {
        // Save updated genealogy data to server automatically

        // Calculate relationships from events
        let relationshipCount = 0;
        Object.values(this.app.events).forEach(event => {
            if (event.type === 'birth') {
                const participants = Object.values(this.app.event_participations)
                    .filter(ep => ep.event_id === event.id);
                const child = participants.find(p => p.role === 'child');
                const parents = participants.filter(p => p.role === 'father' || p.role === 'mother');
                if (child) relationshipCount += parents.length;
            } else if (event.type === 'marriage') {
                const participants = Object.values(this.app.event_participations)
                    .filter(ep => ep.event_id === event.id);
                const spouses = participants.filter(p => p.role === 'groom' || p.role === 'bride');
                if (spouses.length === 2) relationshipCount += 1;
            }
        });

        const data = {
            persons: this.app.persons,
            places: this.app.places,
            events: this.app.events,
            event_participations: this.app.event_participations,
            metadata: {
                total_persons: Object.keys(this.app.persons).length,
                total_events: Object.keys(this.app.events).length,
                total_relationships: relationshipCount,
                last_updated: new Date().toISOString()
            }
        };

        try {
            const response = await fetch('/api/save-data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                console.log('✓ Data saved to data/genealogy_new_model.json');
            } else {
                console.error('Failed to save data:', response.statusText);
            }
        } catch (error) {
            console.error('Error saving data:', error);
        }
    }

    openAddPersonModal() {
        // Reset form
        document.getElementById('add-person-form').reset();
        // Show modal
        document.getElementById('add-person-modal').style.display = 'block';
    }

    closeAddPersonModal() {
        document.getElementById('add-person-modal').style.display = 'none';
    }

    async submitAddPerson(event) {
        event.preventDefault();

        const formData = new FormData(event.target);
        const personData = {};

        // Collect form data
        for (const [key, value] of formData.entries()) {
            if (value) {
                // Convert numeric fields
                if (key === 'birth_year_estimate' || key === 'death_year_estimate' || key === 'marriage_year') {
                    personData[key] = parseInt(value);
                } else if (key === 'tags') {
                    // Step 56: Parse comma-separated tags into array
                    personData[key] = value.split(',').map(t => t.trim()).filter(t => t.length > 0);
                } else {
                    personData[key] = value;
                }
            }
        }

        try {
            // Call API to add person
            const response = await fetch('/api/add-person', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(personData)
            });

            const result = await response.json();

            if (result.success) {
                // Add person to local data
                const newPerson = result.person;
                this.app.persons[newPerson.id] = newPerson;

                // Update local events and participations so birth/death dates are available
                this.app._mergeNewEventsAndParticipations(result.new_events, result.new_participations);

                // Add node to network
                const birthYear = this.app.extractYear(this.app.getPersonBirthDate(newPerson.id));
                const deathYear = this.app.extractYear(this.app.getPersonDeathDate(newPerson.id));
                this.app.network.body.data.nodes.add({
                    id: newPerson.id,
                    label: `${this.app.getFullName(newPerson)}\n(${birthYear || '?'}-${deathYear || '?'})`,
                    color: this.app.getPersonColor(newPerson.gender),
                    shape: 'box'
                });

                // Update stats
                this.app.updateStats();

                // Close modal
                this.closeAddPersonModal();

                // Show success message
                this.showNotification(`Successfully added ${this.app.getFullName(newPerson)} (${newPerson.id})`, 'success');

                // Select the new person
                this.app.network.selectNodes([newPerson.id]);
                this.app.showPersonDetails(newPerson.id);
            } else {
                this.showNotification(`Error: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error adding person:', error);
            this.showNotification('Failed to add person', 'error');
        }
    }

    // Relationship Management
    openAddRelationshipModal() {
        this.relationshipData = {};
        document.getElementById('relationship-step-1').style.display = 'block';
        document.getElementById('relationship-step-2').style.display = 'none';
        document.getElementById('relationship-step-3').style.display = 'none';
        document.getElementById('add-relationship-modal').style.display = 'block';
    }

    closeAddRelationshipModal() {
        document.getElementById('add-relationship-modal').style.display = 'none';
        this.relationshipData = {};
    }

    selectRelationshipType(relType, role) {
        this.relationshipData.type = relType;
        this.relationshipData.role = role;

        const labels = {
            'father': '👨 Adding Father',
            'mother': '👩 Adding Mother',
            'son': '👦 Adding Son',
            'daughter': '👧 Adding Daughter',
            'spouse': '💑 Adding Spouse',
            'godparent': '🙏 Adding Godparent'
        };

        document.getElementById('relationship-type-label').textContent = labels[role] || 'Adding Relationship';
        document.getElementById('relationship-step-1').style.display = 'none';
        document.getElementById('relationship-step-2').style.display = 'block';

        // Set gender based on role
        if (role === 'father' || role === 'son') {
            document.getElementById('rel-gender').value = 'M';
        } else if (role === 'mother' || role === 'daughter') {
            document.getElementById('rel-gender').value = 'F';
        }
    }

    backToRelationshipStep1() {
        document.getElementById('relationship-step-1').style.display = 'block';
        document.getElementById('relationship-step-2').style.display = 'none';
    }

    backToRelationshipStep2() {
        document.getElementById('relationship-step-2').style.display = 'block';
        document.getElementById('relationship-step-3').style.display = 'none';
    }

    searchPersonsForRelationship() {
        const query = document.getElementById('relationship-person-search').value.trim().toLowerCase();

        if (!query) {
            this.showNotification('Please enter a search term', 'warning');
            return;
        }

        const queryParts = query.split(/\s+/);
        const results = [];
        Object.entries(this.app.persons).forEach(([id, person]) => {
            const idMatch = id.toLowerCase().includes(query);
            const allPartsMatch = queryParts.every(part => {
                return (person.first_name || '').toLowerCase().includes(part) ||
                       (person.last_name || '').toLowerCase().includes(part) ||
                       (person.maiden_name || '').toLowerCase().includes(part) ||
                       id.toLowerCase().includes(part);
            });
            if (idMatch || allPartsMatch) {
                results.push({ id, person });
            }
        });

        this.displayRelationshipSearchResults(results);
    }

    displayRelationshipSearchResults(results) {
        const container = document.getElementById('relationship-search-results');

        if (results.length === 0) {
            container.innerHTML = '<div style="text-align: center; padding: 10px; color: #666;">No persons found</div>';
            return;
        }

        let html = `<div style="font-weight: 600; margin-bottom: 10px; color: #333;">Found ${results.length} person(s):</div>`;

        results.forEach(({ id, person }) => {
            const family = this.app.getFamily(id);
            const spouseNames = family.spouses.map(s => {
                const sp = this.app.persons[s.id];
                return sp ? this.app.getFullName(sp) : s.id;
            }).join(', ');

            html += `
                <div class="relationship-search-result">
                    <div class="relationship-search-result-info">
                        <div class="relationship-search-result-name">
                            ${person.first_name} ${person.last_name}
                            ${person.maiden_name ? `<span style="font-weight: normal; color: #888;">(née ${person.maiden_name})</span>` : ''}
                        </div>
                        <div class="relationship-search-result-details">
                            ${id} • ${this.app.extractYear(this.app.getPersonBirthDate(id)) || '?'}-${this.app.extractYear(this.app.getPersonDeathDate(id)) || '?'}
                            ${person.gender ? ` • ${person.gender === 'M' ? 'Male' : person.gender === 'F' ? 'Female' : 'Unknown'}` : ''}
                            ${spouseNames ? ` • Spouse(s): ${spouseNames}` : ''}
                        </div>
                    </div>
                    <button type="button" class="btn-select-person" onclick="editor.selectPersonForRelationship('${id}')">
                        Select
                    </button>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    async selectPersonForRelationship(personId) {
        this.relationshipData.targetPersonId = personId;
        await this.createRelationship();
    }

    createNewPersonForRelationship() {
        document.getElementById('relationship-step-2').style.display = 'none';
        document.getElementById('relationship-step-3').style.display = 'block';

        // Pre-fill form based on relationship type
        document.getElementById('rel-given-name').value = '';
        document.getElementById('rel-surname').value = '';
        document.getElementById('rel-birth-year').value = '';
    }

    async saveNewPersonAndRelationship() {
        const personData = {
            given_name: document.getElementById('rel-given-name').value,
            surname: document.getElementById('rel-surname').value,
            gender: document.getElementById('rel-gender').value,
            birth_year_estimate: parseInt(document.getElementById('rel-birth-year').value) || null
        };

        if (!personData.given_name || !personData.surname) {
            this.showNotification('Please fill in required fields', 'warning');
            return;
        }

        try {
            // Create new person
            const response = await fetch('/api/add-person', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(personData)
            });

            const result = await response.json();

            if (result.success) {
                const newPerson = result.person;

                // Add to local data
                this.app.persons[newPerson.id] = newPerson;
                this.app._mergeNewEventsAndParticipations(result.new_events, result.new_participations);
                const birthYear = this.app.extractYear(this.app.getPersonBirthDate(newPerson.id));
                const deathYear = this.app.extractYear(this.app.getPersonDeathDate(newPerson.id));
                this.app.network.body.data.nodes.add({
                    id: newPerson.id,
                    label: `${this.app.getFullName(newPerson)}\n(${birthYear || '?'}-${deathYear || '?'})`,
                    color: this.app.getPersonColor(newPerson.gender),
                    shape: 'box'
                });

                // Create relationship with this new person
                this.relationshipData.targetPersonId = newPerson.id;
                await this.createRelationship();
            } else {
                this.showNotification(`Error: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error creating person:', error);
            this.showNotification('Failed to create person', 'error');
        }
    }

    async createRelationship() {
        const { type, role, targetPersonId } = this.relationshipData;
        const basePersonId = this.editingPerson;

        try {
            const response = await fetch('/api/add-relationship', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    base_person_id: basePersonId,
                    target_person_id: targetPersonId,
                    relationship_type: type,
                    role: role
                })
            });

            const result = await response.json();

            if (result.success) {
                // Note: Relationships are now event-based
                // The server should have created an appropriate event (birth or marriage)
                // Reload the data to get the new event and participations

                // For now, just reload the network from events
                // This could be optimized later to add edges directly

                // Close modals
                this.closeAddRelationshipModal();

                // Refresh view
                this.app.showPersonDetails(basePersonId);
                this.app.updateStats();

                const targetPerson = this.app.persons[targetPersonId];
                this.showNotification(
                    `Added ${role} relationship with ${this.app.getFullName(targetPerson)}`,
                    'success'
                );
            } else {
                this.showNotification(`Error: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error creating relationship:', error);
            this.showNotification('Failed to create relationship', 'error');
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);

        // Show notification
        setTimeout(() => notification.classList.add('show'), 10);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Initialize editor when app is ready
let editor;
window.addEventListener('load', () => {
    setTimeout(() => {
        if (window.genealogyApp) {
            editor = new GenealogyEditor(window.genealogyApp);
            console.log('Genealogy Editor initialized');
        }
    }, 1000);
});
