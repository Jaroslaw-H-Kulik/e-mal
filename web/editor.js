// Genealogy Editor - Edit and Merge Persons

class GenealogyEditor {
    constructor(app) {
        this.app = app;
        this.editingPerson = null;
        this.mergingPersons = [];
        this.changes = [];  // Track all changes for export
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

            <!-- Changes Summary Modal -->
            <div id="changes-modal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>Changes Summary</h2>
                        <button class="close-modal" onclick="editor.closeChangesModal()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div id="changes-list"></div>
                        <div class="form-actions">
                            <button type="button" class="btn-primary" onclick="editor.exportChanges()">
                                Export Changes
                            </button>
                            <button type="button" class="btn-secondary" onclick="editor.closeChangesModal()">Close</button>
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

        // Step 46: Auto-set gender from Polish given name on blur
        const MALE_NAMES_ENDING_A = ['barnaba', 'bonawentura', 'kuba', 'sasza', 'jarema', 'seba'];
        document.getElementById('edit-given-name').addEventListener('blur', () => {
            const name = document.getElementById('edit-given-name').value.trim().toLowerCase();
            if (!name) return;
            const genderField = document.getElementById('edit-gender');
            if (MALE_NAMES_ENDING_A.includes(name)) {
                genderField.value = 'M';
            } else if (name.endsWith('a')) {
                genderField.value = 'F';
            } else {
                genderField.value = 'M';
            }
        });
    }

    openEditModal(personId) {
        const person = this.app.persons[personId];
        if (!person) return;

        this.editingPerson = personId;

        // Clear GEDCOM lookup results from previous session
        const gedcomResults = document.getElementById('edit-gedcom-lookup-results');
        if (gedcomResults) {
            gedcomResults.innerHTML = '';
        }
        const lookupInput = document.getElementById('edit-lookup-name');
        if (lookupInput) {
            lookupInput.value = '';
        }

        // Fill form with all fields for THIS person
        document.getElementById('edit-id').value = personId;
        document.getElementById('edit-given-name').value = person.first_name || '';
        document.getElementById('edit-surname').value = person.last_name || '';
        document.getElementById('edit-maiden-name').value = person.maiden_name || '';
        document.getElementById('edit-gender').value = person.gender || 'U';
        document.getElementById('edit-birth-year').value = this.app.extractYear(person.birth_date) || '';
        document.getElementById('edit-death-year').value = this.app.extractYear(person.death_date) || '';

        // Clear place fields (using correct IDs from index.html)
        const placeBirthEl = document.getElementById('edit-place-birth');
        const placeDeathEl = document.getElementById('edit-place-death');
        if (placeBirthEl) placeBirthEl.value = '';
        if (placeDeathEl) placeDeathEl.value = '';

        document.getElementById('edit-occupations').value = person.occupation || '';

        // Show modal
        document.getElementById('edit-modal').style.display = 'block';
    }

    closeEditModal() {
        document.getElementById('edit-modal').style.display = 'none';
        this.editingPerson = null;
    }

    async lookupInGedcomForEdit() {
        const searchTerm = document.getElementById('edit-lookup-name').value.trim();

        if (!searchTerm) {
            // Use current person's name if no search term
            const person = this.app.persons[this.editingPerson];
            document.getElementById('edit-lookup-name').value = `${person.first_name} ${person.last_name}`;
            return this.lookupInGedcomForEdit();
        }

        const resultsContainer = document.getElementById('edit-gedcom-lookup-results');
        resultsContainer.innerHTML = '<div style="text-align: center; padding: 20px;">🔍 Searching GEDCOM...</div>';

        try {
            const response = await fetch('/api/gedcom-lookup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ search: searchTerm })
            });

            const result = await response.json();

            if (result.success && result.matches.length > 0) {
                this.displayEditGedcomResults(result.matches);
            } else {
                resultsContainer.innerHTML = `
                    <div class="gedcom-no-results">
                        No matches found in GEDCOM for "${searchTerm}"
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error looking up GEDCOM:', error);
            resultsContainer.innerHTML = `
                <div class="gedcom-no-results" style="color: #e74c3c;">
                    Error searching GEDCOM: ${error.message}
                </div>
            `;
        }
    }

    displayEditGedcomResults(matches) {
        const resultsContainer = document.getElementById('edit-gedcom-lookup-results');

        let html = `<div style="margin-bottom: 10px; font-weight: 600; color: #333;">
            Found ${matches.length} match${matches.length > 1 ? 'es' : ''} in GEDCOM:
        </div>`;

        matches.forEach((match, index) => {
            const currentPerson = this.app.persons[this.editingPerson];
            const birthYear = this.app.extractYear(currentPerson.birth_date);
            const deathYear = this.app.extractYear(currentPerson.death_date);

            html += `
                <div class="gedcom-result-item" style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: white;">
                    <div style="background: #667eea; color: white; padding: 10px; border-radius: 6px; margin-bottom: 15px;">
                        <div style="font-size: 1.1rem; font-weight: 600;">
                            ${match.given_name || '?'} ${match.surname || '?'}
                            ${match.maiden_name ? `(née ${match.maiden_name})` : ''}
                        </div>
                        <div style="font-size: 0.9rem; margin-top: 5px;">
                            ${match.gender} • ${match.birth_year || '?'} - ${match.death_year || '?'}
                        </div>
                        ${match.father_name || match.mother_name ? `
                            <div style="font-size: 0.85rem; color: #e0e7ff; margin-top: 4px;">
                                ${match.father_name ? `👨 Father: ${match.father_name}` : ''}
                                ${match.father_name && match.mother_name ? ' • ' : ''}
                                ${match.mother_name ? `👩 Mother: ${match.mother_name}` : ''}
                            </div>
                        ` : ''}
                    </div>

                    <!-- Importable Fields -->
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 10px;">
                        <div style="font-weight: 600; margin-bottom: 10px; color: #333;">Select fields to import:</div>
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                            ${!currentPerson.maiden_name && match.maiden_name ? `
                                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                    <input type="checkbox" class="gedcom-import-field" data-field="maiden-name" data-value="${match.maiden_name || ''}" data-index="${index}">
                                    <span>Maiden Name: <strong>${match.maiden_name}</strong></span>
                                </label>
                            ` : ''}
                            ${!currentPerson.gender && match.gender ? `
                                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                    <input type="checkbox" class="gedcom-import-field" data-field="gender" data-value="${match.gender || ''}" data-index="${index}">
                                    <span>Gender: <strong>${match.gender}</strong></span>
                                </label>
                            ` : ''}
                            ${!birthYear && match.birth_year ? `
                                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                    <input type="checkbox" class="gedcom-import-field" data-field="birth-year" data-value="${match.birth_year || ''}" data-index="${index}">
                                    <span>Birth Year: <strong>${match.birth_year}</strong></span>
                                </label>
                            ` : ''}
                            ${!deathYear && match.death_year ? `
                                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                    <input type="checkbox" class="gedcom-import-field" data-field="death-year" data-value="${match.death_year || ''}" data-index="${index}">
                                    <span>Death Year: <strong>${match.death_year}</strong></span>
                                </label>
                            ` : ''}
                            ${match.birth_place ? `
                                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                    <input type="checkbox" class="gedcom-import-field" data-field="place-birth" data-value="${match.birth_place || ''}" data-index="${index}">
                                    <span>Birth Place: <strong>${match.birth_place}</strong></span>
                                </label>
                            ` : ''}
                            ${match.death_place ? `
                                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                    <input type="checkbox" class="gedcom-import-field" data-field="place-death" data-value="${match.death_place || ''}" data-index="${index}">
                                    <span>Death Place: <strong>${match.death_place}</strong></span>
                                </label>
                            ` : ''}
                            ${!currentPerson.occupation && match.occupation ? `
                                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                    <input type="checkbox" class="gedcom-import-field" data-field="occupations" data-value="${match.occupation || ''}" data-index="${index}">
                                    <span>Occupation: <strong>${match.occupation}</strong></span>
                                </label>
                            ` : ''}
                        </div>
                        <button type="button" class="btn-primary" style="margin-top: 10px; padding: 8px 16px;" onclick="editor.importSelectedGedcomFields(${index})">
                            Import Selected Fields
                        </button>
                    </div>

                    <!-- Events -->
                    ${match.events && match.events.length > 0 ? `
                        <div style="background: #fff3cd; padding: 15px; border-radius: 6px; margin-bottom: 10px;">
                            <div style="font-weight: 600; margin-bottom: 10px; color: #333;">📅 Events (${match.events.length}):</div>
                            ${match.events.map(evt => `
                                <div style="padding: 5px 0; border-bottom: 1px solid #e0e0e0; font-size: 0.9rem;">
                                    <strong>${evt.type}</strong>
                                    ${evt.date && evt.date.year ? `- ${evt.date.year}` : ''}
                                    ${evt.place ? `- ${evt.place}` : ''}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}

                    <!-- Relationships -->
                    <div style="background: #e3f2fd; padding: 15px; border-radius: 6px;">
                        <div style="font-weight: 600; margin-bottom: 10px; color: #333;">👪 Relationships:</div>

                        ${match.father_name || match.mother_name ? `
                            <div style="margin-bottom: 10px;">
                                <strong>Parents:</strong>
                                ${match.father_name ? `
                                    <div style="margin-left: 15px; display: flex; align-items: center; justify-content: space-between; margin-top: 5px;">
                                        <span>• Father: ${match.father_name}</span>
                                        <button type="button" class="btn-small" onclick="editor.openGedcomRelationModal(${index}, 'father')" style="padding: 4px 12px; font-size: 0.85rem;">
                                            ➕ Add
                                        </button>
                                    </div>
                                ` : ''}
                                ${match.mother_name ? `
                                    <div style="margin-left: 15px; display: flex; align-items: center; justify-content: space-between; margin-top: 5px;">
                                        <span>• Mother: ${match.mother_name}</span>
                                        <button type="button" class="btn-small" onclick="editor.openGedcomRelationModal(${index}, 'mother')" style="padding: 4px 12px; font-size: 0.85rem;">
                                            ➕ Add
                                        </button>
                                    </div>
                                ` : ''}
                            </div>
                        ` : ''}

                        ${match.spouses && match.spouses.length > 0 ? `
                            <div style="margin-bottom: 10px;">
                                <strong>Spouse(s):</strong>
                                ${match.spouses.map((s, sIndex) => `
                                    <div style="margin-left: 15px; display: flex; align-items: center; justify-content: space-between; margin-top: 5px;">
                                        <span>• ${s.name}</span>
                                        <button type="button" class="btn-small" onclick="editor.openGedcomRelationModal(${index}, 'spouse', ${sIndex})" style="padding: 4px 12px; font-size: 0.85rem;">
                                            ➕ Add
                                        </button>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}

                        ${match.children && match.children.length > 0 ? `
                            <div>
                                <strong>Children (${match.children.length}):</strong>
                                ${match.children.map((c, cIndex) => `
                                    <div style="margin-left: 15px; display: flex; align-items: center; justify-content: space-between; margin-top: 5px;">
                                        <span>• ${c.name}</span>
                                        <button type="button" class="btn-small" onclick="editor.openGedcomRelationModal(${index}, 'child', ${cIndex})" style="padding: 4px 12px; font-size: 0.85rem;">
                                            ➕ Add
                                        </button>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        });

        resultsContainer.innerHTML = html;

        // Store matches for selection
        this.editGedcomMatches = matches;
    }

    importSelectedGedcomFields(index) {
        const checkboxes = document.querySelectorAll(`.gedcom-import-field[data-index="${index}"]:checked`);

        if (checkboxes.length === 0) {
            this.showNotification('Please select at least one field to import', 'warning');
            return;
        }

        let importedCount = 0;
        checkboxes.forEach(checkbox => {
            const field = checkbox.dataset.field;
            const value = checkbox.dataset.value;

            // Map GEDCOM fields to form field IDs
            const inputElement = document.getElementById(`edit-${field}`);

            if (inputElement) {
                inputElement.value = value;
                importedCount++;
                console.log(`Imported ${field} = ${value}`);
            } else {
                console.warn(`Form field not found: edit-${field}`);
            }
        });

        this.showNotification(`Imported ${importedCount} field${importedCount > 1 ? 's' : ''} from GEDCOM`, 'success');

        // Scroll to form
        document.getElementById('edit-person-form').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    async savePersonEdit(event) {
        if (event) event.preventDefault();

        const personId = this.editingPerson;
        const person = this.app.persons[personId];

        const oldData = { ...person };

        // Get birth and death years from form
        const birthYearInput = parseInt(document.getElementById('edit-birth-year').value) || null;
        const deathYearInput = parseInt(document.getElementById('edit-death-year').value) || null;

        // Get place values
        const placeBirth = document.getElementById('edit-place-birth')?.value.trim() || null;
        const placeDeath = document.getElementById('edit-place-death')?.value.trim() || null;

        const updateData = {
            person_id: personId,
            first_name: document.getElementById('edit-given-name').value,
            last_name: document.getElementById('edit-surname').value,
            maiden_name: document.getElementById('edit-maiden-name').value || null,
            gender: document.getElementById('edit-gender').value,
            birth_date: birthYearInput ? { year: birthYearInput, month: null, day: null, circa: true } : null,
            death_date: deathYearInput ? { year: deathYearInput, month: null, day: null, circa: true } : null,
            occupation: document.getElementById('edit-occupations').value || null,
            place_of_birth: placeBirth,
            place_of_death: placeDeath
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

                // Track change
                this.changes.push({
                    type: 'edit',
                    personId: personId,
                    timestamp: new Date().toISOString(),
                    oldData: oldData,
                    newData: result.person
                });

                // Update network
                const birthYear = this.app.extractYear(result.person.birth_date);
                const deathYear = this.app.extractYear(result.person.death_date);
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
                    ${personId} • ${this.app.extractYear(person.birth_date) || '?'}-${this.app.extractYear(person.death_date) || '?'}
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

        // Track merge
        this.changes.push({
            type: 'merge',
            timestamp: new Date().toISOString(),
            keptPerson: keepId,
            mergedPerson: mergeId,
            keptData: { ...keepPerson },
            mergedData: { ...mergePerson }
        });

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

        // Auto-save merge log to server
        this.saveMergeLogToServer();

        // Auto-save updated data
        this.saveDataToServer();

        // Close modal
        this.closeMergeModal();

        // Refresh view
        this.app.showPersonDetails(keepId);
        this.app.network.selectNodes([keepId]);

        this.showNotification(`Successfully merged ${mergeId} into ${keepId}`, 'success');
    }

    showChangesModal() {
        if (this.changes.length === 0) {
            this.showNotification('No changes made yet', 'info');
            return;
        }

        const list = document.getElementById('changes-list');
        let html = `<div class="changes-summary">
            <p>Total changes: ${this.changes.length}</p>
            <ul class="changes-log">`;

        this.changes.forEach((change, idx) => {
            if (change.type === 'edit') {
                html += `<li><strong>Edit:</strong> ${change.personId} - ${change.newData.given_name} ${change.newData.surname}</li>`;
            } else if (change.type === 'merge') {
                html += `<li><strong>Merge:</strong> ${change.mergedPerson} → ${change.keptPerson}</li>`;
            }
        });

        html += '</ul></div>';
        list.innerHTML = html;

        document.getElementById('changes-modal').style.display = 'flex';
    }

    closeChangesModal() {
        document.getElementById('changes-modal').style.display = 'none';
    }

    exportChanges() {
        const timestamp = Date.now();

        // Create full export data
        const exportData = {
            persons: this.app.persons,
            events: this.app.events,
            relationships: this.app.relationships,
            changes_log: this.changes,
            exported_at: new Date().toISOString()
        };

        // Download full data
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `genealogy_edited_${timestamp}.json`;
        a.click();
        URL.revokeObjectURL(url);

        // Create separate merge log for parser
        const mergeLog = {
            instructions: "This file contains merge records. The parser will automatically apply these merges when processing base.md to avoid recreating duplicates.",
            merges: this.changes
                .filter(c => c.type === 'merge')
                .map(c => ({
                    kept_person: c.keptPerson,
                    merged_person: c.mergedPerson,
                    kept_name: `${c.keptData.given_name} ${c.keptData.surname}`,
                    merged_name: `${c.mergedData.given_name} ${c.mergedData.surname}`,
                    timestamp: c.timestamp
                })),
            total_merges: this.changes.filter(c => c.type === 'merge').length,
            last_updated: new Date().toISOString()
        };

        // Download merge log
        const mergeBlob = new Blob([JSON.stringify(mergeLog, null, 2)], { type: 'application/json' });
        const mergeUrl = URL.createObjectURL(mergeBlob);
        const mergeLink = document.createElement('a');
        mergeLink.href = mergeUrl;
        mergeLink.download = `merge_log_${timestamp}.json`;
        mergeLink.click();
        URL.revokeObjectURL(mergeUrl);

        this.showNotification('Changes and merge log exported successfully!', 'success');
    }

    async saveMergeLogToServer() {
        // Save merge log to server automatically
        const mergeLog = {
            merges: this.changes
                .filter(c => c.type === 'merge')
                .map(c => ({
                    kept_person: c.keptPerson,
                    merged_person: c.mergedPerson,
                    kept_name: `${c.keptData.given_name} ${c.keptData.surname}`,
                    merged_name: `${c.mergedData.given_name} ${c.mergedData.surname}`,
                    timestamp: c.timestamp
                })),
            last_updated: new Date().toISOString()
        };

        try {
            const response = await fetch('/api/save-merge-log', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(mergeLog)
            });

            if (response.ok) {
                console.log('✓ Merge log saved to data/merge_log.json');
            } else {
                console.error('Failed to save merge log:', response.statusText);
            }
        } catch (error) {
            console.error('Error saving merge log:', error);
        }
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
        document.getElementById('lookup-name').value = '';
        document.getElementById('gedcom-lookup-results').innerHTML = '';
        // Show modal
        document.getElementById('add-person-modal').style.display = 'block';
    }

    closeAddPersonModal() {
        document.getElementById('add-person-modal').style.display = 'none';
    }

    async lookupInGedcom() {
        const searchTerm = document.getElementById('lookup-name').value.trim();

        if (!searchTerm) {
            this.showNotification('Please enter a name to search', 'warning');
            return;
        }

        const resultsContainer = document.getElementById('gedcom-lookup-results');
        resultsContainer.innerHTML = '<div style="text-align: center; padding: 20px;">🔍 Searching GEDCOM...</div>';

        try {
            const response = await fetch('/api/gedcom-lookup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ search: searchTerm })
            });

            const result = await response.json();

            if (result.success && result.matches.length > 0) {
                this.displayGedcomResults(result.matches);
            } else {
                resultsContainer.innerHTML = `
                    <div class="gedcom-no-results">
                        No matches found in GEDCOM for "${searchTerm}"
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error looking up GEDCOM:', error);
            resultsContainer.innerHTML = `
                <div class="gedcom-no-results" style="color: #e74c3c;">
                    Error searching GEDCOM: ${error.message}
                </div>
            `;
        }
    }

    displayGedcomResults(matches) {
        const resultsContainer = document.getElementById('gedcom-lookup-results');

        let html = `<div style="margin-bottom: 10px; font-weight: 600; color: #333;">
            Found ${matches.length} match${matches.length > 1 ? 'es' : ''} in GEDCOM:
        </div>`;

        matches.forEach((match, index) => {
            html += `
                <div class="gedcom-result-item">
                    <div class="gedcom-result-header">
                        <div class="gedcom-result-name">
                            ${match.given_name || '?'} ${match.surname || '?'}
                            ${match.maiden_name ? `(née ${match.maiden_name})` : ''}
                        </div>
                        <button type="button" class="btn-select-gedcom" onclick="editor.selectGedcomPerson(${index})">
                            Select This Person
                        </button>
                    </div>
                    <div class="gedcom-result-details">
                        <div class="gedcom-result-detail">
                            <strong>Gender:</strong>
                            <span>${match.gender === 'M' ? 'Male' : match.gender === 'F' ? 'Female' : 'Unknown'}</span>
                        </div>
                        <div class="gedcom-result-detail">
                            <strong>Birth:</strong>
                            <span>${match.birth_date || match.birth_year || '?'}${match.birth_place ? ` in ${match.birth_place}` : ''}</span>
                        </div>
                        <div class="gedcom-result-detail">
                            <strong>Death:</strong>
                            <span>${match.death_date || match.death_year || '?'}${match.death_place ? ` in ${match.death_place}` : ''}</span>
                        </div>
                        <div class="gedcom-result-detail">
                            <strong>Marriage:</strong>
                            <span>${match.marriage_year || '?'}</span>
                        </div>
                        ${match.father_name || match.mother_name ? `
                            <div class="gedcom-result-detail" style="grid-column: 1 / -1; background: #f0f8ff; padding: 8px; border-radius: 4px; margin-top: 8px;">
                                <strong>👪 Parents:</strong>
                                <div style="margin-top: 4px;">
                                    ${match.father_name ? `<div>• Father: ${match.father_name}</div>` : ''}
                                    ${match.mother_name ? `<div>• Mother: ${match.mother_name}</div>` : ''}
                                </div>
                            </div>
                        ` : ''}
                        ${match.spouse ? `
                            <div class="gedcom-result-detail" style="grid-column: 1 / -1;">
                                <strong>Spouse:</strong>
                                <span>${match.spouse}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        });

        resultsContainer.innerHTML = html;

        // Store matches for selection
        this.gedcomMatches = matches;
    }

    selectGedcomPerson(index) {
        const person = this.gedcomMatches[index];

        // Fill form with GEDCOM data
        document.getElementById('add-given-name').value = person.first_name || '';
        document.getElementById('add-surname').value = person.last_name || '';
        document.getElementById('add-maiden-name').value = person.maiden_name || '';
        document.getElementById('add-gender').value = person.gender || 'U';
        document.getElementById('add-birth-year').value = person.birth_year || '';
        document.getElementById('add-death-year').value = person.death_year || '';
        document.getElementById('add-place-birth').value = person.birth_place || '';
        document.getElementById('add-place-death').value = person.death_place || '';
        document.getElementById('add-marriage-year').value = person.marriage_year || '';

        this.showNotification(`Filled form with data for ${person.first_name} ${person.last_name}`, 'success');

        // Scroll to form
        document.getElementById('add-person-form').scrollIntoView({ behavior: 'smooth', block: 'start' });
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

                // Add node to network
                const birthYear = this.app.extractYear(newPerson.birth_date);
                const deathYear = this.app.extractYear(newPerson.death_date);
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

        const results = [];
        Object.entries(this.app.persons).forEach(([id, person]) => {
            const fullName = `${person.first_name} ${person.last_name}`.toLowerCase();
            if (fullName.includes(query) || id.toLowerCase().includes(query)) {
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
            html += `
                <div class="relationship-search-result">
                    <div class="relationship-search-result-info">
                        <div class="relationship-search-result-name">
                            ${person.first_name} ${person.last_name}
                        </div>
                        <div class="relationship-search-result-details">
                            ${id} • ${this.app.extractYear(person.birth_date) || '?'}-${this.app.extractYear(person.death_date) || '?'}
                            ${person.gender ? ` • ${person.gender === 'M' ? 'Male' : person.gender === 'F' ? 'Female' : 'Unknown'}` : ''}
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
                const birthYear = this.app.extractYear(newPerson.birth_date);
                const deathYear = this.app.extractYear(newPerson.death_date);
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

    // ==================== GEDCOM Relationship Add/Merge Functions ====================

    openGedcomRelationModal(matchIndex, relationType, relationIndex = 0) {
        const match = this.editGedcomMatches[matchIndex];
        if (!match) return;

        // Store context
        this.gedcomRelationContext = {
            matchIndex,
            relationType,
            relationIndex,
            match
        };

        // Get the specific relation data
        let relationData;
        let relationLabel;

        if (relationType === 'father') {
            relationData = match.parents?.father;
            relationLabel = 'Father';
        } else if (relationType === 'mother') {
            relationData = match.parents?.mother;
            relationLabel = 'Mother';
        } else if (relationType === 'spouse') {
            relationData = match.spouses[relationIndex];
            relationLabel = 'Spouse';
        } else if (relationType === 'child') {
            relationData = match.children[relationIndex];
            relationLabel = 'Child';
        }

        if (!relationData) return;

        this.gedcomRelationContext.relationData = relationData;

        // Display person info
        const personInfo = document.getElementById('gedcom-relation-person-info');
        personInfo.innerHTML = `
            <div style="font-size: 1.1rem; font-weight: 600;">${relationData.name}</div>
            <div style="font-size: 0.9rem; margin-top: 5px;">GEDCOM ID: ${relationData.id}</div>
        `;

        // Display relationship type
        const currentPerson = this.app.persons[this.editingPerson];
        const typeInfo = document.getElementById('gedcom-relation-type-info');
        typeInfo.innerHTML = `
            <div><strong>Relationship:</strong> ${relationLabel} of ${this.app.getFullName(currentPerson)}</div>
        `;

        // Reset modal state
        document.getElementById('gedcom-relation-action-selection').style.display = 'block';
        document.getElementById('gedcom-relation-merge-section').style.display = 'none';
        document.getElementById('gedcom-merge-fields').style.display = 'none';
        document.getElementById('gedcom-merge-search').value = '';
        document.getElementById('gedcom-merge-results').innerHTML = '';

        // Show modal
        document.getElementById('gedcom-relation-modal').style.display = 'block';
    }

    closeGedcomRelationModal() {
        document.getElementById('gedcom-relation-modal').style.display = 'none';
        this.gedcomRelationContext = null;
    }

    async addGedcomRelationAsNew() {
        const ctx = this.gedcomRelationContext;
        if (!ctx) return;

        try {
            // Fetch full person data from GEDCOM
            const response = await fetch(`/api/gedcom-person/${ctx.relationData.id}`);
            const result = await response.json();

            if (!result.success) {
                this.showNotification(`Error: ${result.error}`, 'error');
                return;
            }

            const gedcomPerson = result.person;

            // Create new person
            const newPerson = {
                first_name: gedcomPerson.first_name || '',
                last_name: gedcomPerson.last_name || '',
                maiden_name: gedcomPerson.maiden_name || '',
                gender: gedcomPerson.gender || 'U',
                birth_date: gedcomPerson.birth_date || null,
                death_date: gedcomPerson.death_date || null,
                occupation: gedcomPerson.occupation || ''
            };

            const createResponse = await fetch('/api/add-person', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newPerson)
            });

            const createResult = await createResponse.json();

            if (createResult.success) {
                // Add to local data
                this.app.persons[createResult.person.id] = createResult.person;

                // Open event editor with pre-populated data (Step 24)
                this.openEventEditorForGedcomRelation(createResult.person.id);

                this.showNotification(`Added ${this.app.getFullName(createResult.person)}. Now configure the relationship event.`, 'success');
                this.closeGedcomRelationModal();

                // Refresh the person details view
                this.app.showPersonDetails(this.editingPerson);
                this.app.updateStats();
            } else {
                this.showNotification(`Error: ${createResult.error}`, 'error');
            }
        } catch (error) {
            console.error('Error adding person from GEDCOM:', error);
            this.showNotification('Failed to add person', 'error');
        }
    }

    showMergeWithExisting() {
        document.getElementById('gedcom-relation-action-selection').style.display = 'none';
        document.getElementById('gedcom-relation-merge-section').style.display = 'block';

        // Setup search
        const searchInput = document.getElementById('gedcom-merge-search');
        searchInput.addEventListener('input', () => this.searchPersonsForMerge());

        // Pre-populate with GEDCOM person's name
        const ctx = this.gedcomRelationContext;
        if (ctx && ctx.relationData && ctx.relationData.name) {
            searchInput.value = ctx.relationData.name;
        }

        // Initial search with pre-populated name
        this.searchPersonsForMerge();
    }

    searchPersonsForMerge() {
        const query = document.getElementById('gedcom-merge-search').value.toLowerCase();
        const resultsContainer = document.getElementById('gedcom-merge-results');

        const matches = Object.entries(this.app.persons)
            .filter(([id, person]) => {
                if (!query) return true; // Show all if no query
                const fullName = this.app.getFullName(person).toLowerCase();
                return fullName.includes(query) || id.toLowerCase().includes(query);
            })
            .slice(0, 20); // Limit to 20 results

        if (matches.length === 0) {
            resultsContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: #999;">No persons found</div>';
            return;
        }

        resultsContainer.innerHTML = matches.map(([id, person]) => {
            const birthYear = this.app.extractYear(person.birth_date);
            const deathYear = this.app.extractYear(person.death_date);

            return `
                <div style="padding: 10px; border-bottom: 1px solid #eee; cursor: pointer; border-radius: 4px;"
                     onmouseover="this.style.background='#f5f5f5'"
                     onmouseout="this.style.background='white'"
                     onclick="editor.selectPersonForMerge('${id}', event)">
                    <div style="font-weight: 600;">${this.app.getFullName(person)}</div>
                    <div style="font-size: 0.85rem; color: #666;">
                        ${id} • ${birthYear || '?'} - ${deathYear || '?'}
                        ${person.gender ? ` • ${person.gender}` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }

    async selectPersonForMerge(personId) {
        const person = this.app.persons[personId];
        if (!person) return;

        this.gedcomRelationContext.mergeTargetId = personId;

        // Fetch full GEDCOM data
        const ctx = this.gedcomRelationContext;
        try {
            if (!ctx || !ctx.relationData || !ctx.relationData.id) {
                console.error('Invalid GEDCOM relation context:', ctx);
                this.showNotification('Invalid relationship data', 'error');
                return;
            }

            const gedcomId = ctx.relationData.id;
            console.log(`Fetching GEDCOM person: ${gedcomId}`);

            const response = await fetch(`/api/gedcom-person/${gedcomId}`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();

            if (!result.success) {
                this.showNotification(`Error: ${result.error}`, 'error');
                return;
            }

            const gedcomPerson = result.person;

            // Show field selection
            const fieldsContainer = document.getElementById('gedcom-merge-field-list');
            const fields = [];

            // Check which fields can be imported
            if (!person.maiden_name && gedcomPerson.maiden_name) {
                fields.push({ field: 'maiden_name', label: 'Maiden Name', value: gedcomPerson.maiden_name });
            }
            if (!this.app.extractYear(person.birth_date) && gedcomPerson.birth_date?.year) {
                fields.push({ field: 'birth_date', label: 'Birth Date', value: this.app.formatFlexibleDate(gedcomPerson.birth_date) });
            }
            if (!this.app.extractYear(person.death_date) && gedcomPerson.death_date?.year) {
                fields.push({ field: 'death_date', label: 'Death Date', value: this.app.formatFlexibleDate(gedcomPerson.death_date) });
            }
            if (!person.occupation && gedcomPerson.occupation) {
                fields.push({ field: 'occupation', label: 'Occupation', value: gedcomPerson.occupation });
            }

            if (fields.length === 0) {
                fieldsContainer.innerHTML = '<div style="grid-column: 1 / -1; padding: 10px; text-align: center; color: #666;">No new fields to import</div>';
            } else {
                fieldsContainer.innerHTML = fields.map(f => `
                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                        <input type="checkbox" class="gedcom-merge-field-checkbox" data-field="${f.field}" data-value='${JSON.stringify(gedcomPerson[f.field])}' checked>
                        <span>${f.label}: <strong>${f.value}</strong></span>
                    </label>
                `).join('');
            }

            document.getElementById('gedcom-merge-fields').style.display = 'block';

            // Highlight selected person
            document.querySelectorAll('#gedcom-merge-results > div').forEach(el => {
                el.style.background = 'white';
            });
            if (event && event.target) {
                event.target.closest('div').style.background = '#e3f2fd';
            }

        } catch (error) {
            console.error('Error fetching GEDCOM person:', error);
            this.showNotification(`Failed to fetch GEDCOM data: ${error.message}`, 'error');
        }
    }

    async confirmMergeGedcomRelation() {
        const ctx = this.gedcomRelationContext;
        if (!ctx || !ctx.mergeTargetId) return;

        try {
            const targetPerson = this.app.persons[ctx.mergeTargetId];

            // Get selected fields
            const checkboxes = document.querySelectorAll('.gedcom-merge-field-checkbox:checked');
            const updates = {};

            checkboxes.forEach(cb => {
                const field = cb.dataset.field;
                const value = JSON.parse(cb.dataset.value);
                updates[field] = value;
            });

            // Update person if there are fields to merge
            if (Object.keys(updates).length > 0) {
                // Add person_id to the updates object for the API
                updates.person_id = ctx.mergeTargetId;

                const updateResponse = await fetch('/api/update-person', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updates)
                });

                const updateResult = await updateResponse.json();

                if (updateResult.success) {
                    // Update local data
                    Object.assign(this.app.persons[ctx.mergeTargetId], updates);
                } else {
                    this.showNotification(`Error updating person: ${updateResult.error}`, 'error');
                    return;
                }
            }

            // Open event editor with pre-populated data (Step 24)
            this.openEventEditorForGedcomRelation(ctx.mergeTargetId);

            this.showNotification(`Merged data with ${this.app.getFullName(targetPerson)}. Now configure the relationship event.`, 'success');
            this.closeGedcomRelationModal();

            // Refresh view
            this.app.showPersonDetails(this.editingPerson);
            this.app.updateStats();

        } catch (error) {
            console.error('Error merging GEDCOM relation:', error);
            this.showNotification('Failed to merge', 'error');
        }
    }

    openEventEditorForGedcomRelation(relatedPersonId) {
        // Step 24: Open event editor with pre-populated participants from GEDCOM
        const ctx = this.gedcomRelationContext;
        const currentPerson = this.app.persons[this.editingPerson];
        const relatedPerson = this.app.persons[relatedPersonId];
        const match = ctx.match;

        // Determine event type and check for existing event
        let eventType, existingEventId, participants;

        if (ctx.relationType === 'father' || ctx.relationType === 'mother') {
            // Birth event: current person is child, adding parent(s)
            eventType = 'birth';

            // Check if current person already has a birth event
            existingEventId = this.findBirthEventForPerson(this.editingPerson);

            participants = [
                { role: 'child', personId: this.editingPerson }
            ];

            // Add father if available in GEDCOM
            if (match.parents?.father) {
                const fatherInSystem = this.findPersonByGedcomId(match.parents.father.id);
                if (fatherInSystem) {
                    participants.push({ role: 'father', personId: fatherInSystem.id });
                }
            }

            // Add mother if available in GEDCOM
            if (match.parents?.mother) {
                const motherInSystem = this.findPersonByGedcomId(match.parents.mother.id);
                if (motherInSystem) {
                    participants.push({ role: 'mother', personId: motherInSystem.id });
                }
            }

            // If the related person is one of the parents and not yet added, add them
            if (ctx.relationType === 'father' && !participants.find(p => p.personId === relatedPersonId)) {
                participants.push({ role: 'father', personId: relatedPersonId });
            }
            if (ctx.relationType === 'mother' && !participants.find(p => p.personId === relatedPersonId)) {
                participants.push({ role: 'mother', personId: relatedPersonId });
            }

        } else if (ctx.relationType === 'spouse') {
            // Marriage event
            eventType = 'marriage';

            // Check if there's already a marriage event between these two people
            existingEventId = this.findMarriageEventBetween(this.editingPerson, relatedPersonId);

            const currentRole = currentPerson.gender === 'M' ? 'groom' : 'bride';
            const relatedRole = relatedPerson.gender === 'M' ? 'groom' : 'bride';

            participants = [
                { role: currentRole, personId: this.editingPerson },
                { role: relatedRole, personId: relatedPersonId }
            ];

        } else if (ctx.relationType === 'child') {
            // Birth event: related person is child, current person is parent
            eventType = 'birth';

            // Check if child already has a birth event
            existingEventId = this.findBirthEventForPerson(relatedPersonId);

            const parentRole = currentPerson.gender === 'M' ? 'father' : 'mother';

            participants = [
                { role: 'child', personId: relatedPersonId },
                { role: parentRole, personId: this.editingPerson }
            ];
        }

        // Close the GEDCOM relation modal
        this.closeGedcomRelationModal();

        // Open event editor (eventEditor is a global variable from event-editor.js)
        if (typeof eventEditor === 'undefined') {
            this.showNotification('Event editor not initialized yet', 'error');
            return;
        }

        if (existingEventId) {
            // Edit existing event
            console.log(`Step 24: Opening existing ${eventType} event ${existingEventId} for editing`);
            eventEditor.openEditEventModal(existingEventId);

            // Wait for form to load, then add the new participant
            setTimeout(() => {
                // Only add participants that aren't already in the event
                participants.forEach(p => {
                    const currentValue = document.getElementById(`${p.role}_person_id`)?.value;
                    if (!currentValue) {
                        // This role is empty, add the participant
                        eventEditor.selectExistingPerson(p.role, p.personId);
                        console.log(`Step 24: Added ${p.role} ${p.personId} to existing event`);
                    }
                });
            }, 100);
        } else {
            // Create new event
            console.log(`Step 24: Creating new ${eventType} event`);
            eventEditor.openAddEventModal(this.editingPerson);
            eventEditor.selectEventType(eventType);

            // Wait a brief moment for the form to be built, then pre-populate
            setTimeout(() => {
                participants.forEach(p => {
                    eventEditor.selectExistingPerson(p.role, p.personId);
                });
                console.log(`Step 24: Pre-populated ${participants.length} participants in new ${eventType} event`);
            }, 100);
        }
    }

    findBirthEventForPerson(personId) {
        // Find birth event where this person is the child
        for (const ep of Object.values(this.app.event_participations)) {
            if (ep.person_id === personId && ep.role === 'child') {
                const event = this.app.events[ep.event_id];
                if (event && (event.type === 'birth' || event.type === 'baptism')) {
                    return ep.event_id;
                }
            }
        }
        return null;
    }

    findMarriageEventBetween(personId1, personId2) {
        // Find marriage event between two people
        const person1Events = new Set();

        // Collect all marriage events where person1 participates
        for (const ep of Object.values(this.app.event_participations)) {
            if (ep.person_id === personId1) {
                const event = this.app.events[ep.event_id];
                if (event && event.type === 'marriage') {
                    person1Events.add(ep.event_id);
                }
            }
        }

        // Check if person2 participates in any of those events
        for (const ep of Object.values(this.app.event_participations)) {
            if (ep.person_id === personId2 && person1Events.has(ep.event_id)) {
                return ep.event_id;
            }
        }

        return null;
    }

    findPersonByGedcomId(gedcomId) {
        // Search for a person in our system that has this GEDCOM ID
        for (const person of Object.values(this.app.persons)) {
            if (person.gedcom_id === gedcomId) {
                return person;
            }
        }
        return null;
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
