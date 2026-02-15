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
    }

    openEditModal(personId) {
        const person = this.app.persons[personId];
        if (!person) return;

        this.editingPerson = personId;

        // Fill form
        document.getElementById('edit-id').value = personId;
        document.getElementById('edit-given-name').value = person.given_name || '';
        document.getElementById('edit-surname').value = person.surname || '';
        document.getElementById('edit-maiden-name').value = person.maiden_name || '';
        document.getElementById('edit-gender').value = person.gender || 'U';
        document.getElementById('edit-birth-year').value = person.birth_year_estimate || '';
        document.getElementById('edit-death-year').value = person.death_year_estimate || '';
        document.getElementById('edit-occupations').value = person.occupations ? person.occupations.join(', ') : '';

        // Show modal
        document.getElementById('edit-modal').style.display = 'flex';
    }

    closeEditModal() {
        document.getElementById('edit-modal').style.display = 'none';
        this.editingPerson = null;
    }

    savePersonEdit() {
        const personId = this.editingPerson;
        const person = this.app.persons[personId];

        const oldData = { ...person };
        const newData = {
            given_name: document.getElementById('edit-given-name').value,
            surname: document.getElementById('edit-surname').value,
            maiden_name: document.getElementById('edit-maiden-name').value || null,
            gender: document.getElementById('edit-gender').value,
            birth_year_estimate: parseInt(document.getElementById('edit-birth-year').value) || null,
            death_year_estimate: parseInt(document.getElementById('edit-death-year').value) || null,
            occupations: document.getElementById('edit-occupations').value.split(',').map(s => s.trim()).filter(Boolean)
        };

        // Update person
        Object.assign(person, newData);

        // Track change
        this.changes.push({
            type: 'edit',
            personId: personId,
            timestamp: new Date().toISOString(),
            oldData: oldData,
            newData: newData
        });

        // Update network
        this.app.network.body.data.nodes.update({
            id: personId,
            label: `${newData.given_name} ${newData.surname}\n(${newData.birth_year_estimate || '?'}-${newData.death_year_estimate || '?'})`,
            color: this.app.getPersonColor(newData.gender)
        });

        // Refresh person details
        this.app.showPersonDetails(personId);

        this.closeEditModal();

        // Show success message
        this.showNotification('Person updated successfully!', 'success');
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
                <strong>${person.given_name} ${person.surname}</strong>
                <div class="person-meta">
                    ${personId} • ${person.birth_year_estimate || '?'}-${person.death_year_estimate || '?'}
                </div>
                ${person.maiden_name ? `<div>Maiden: ${person.maiden_name}</div>` : ''}
            </div>
            <button class="btn-small" onclick="editor.clearMergeSelection(${this.mergingPersons.length})">Clear</button>
        `;

        // Show notification about selection
        if (this.mergingPersons.length === 1) {
            this.showNotification(`Selected ${person.given_name} ${person.surname}. Select one more person to merge.`, 'info');
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

        // Update all relationships
        Object.values(this.app.relationships).forEach(rel => {
            if (rel.from_person === mergeId) {
                rel.from_person = keepId;
            }
            if (rel.to_person === mergeId) {
                rel.to_person = keepId;
            }
        });

        // Update all events
        Object.values(this.app.events).forEach(event => {
            ['child', 'father', 'mother', 'deceased', 'groom', 'bride'].forEach(field => {
                if (event[field] === mergeId) {
                    event[field] = keepId;
                }
            });
            ['witnesses', 'godparents'].forEach(field => {
                if (event[field]) {
                    event[field] = event[field].map(id => id === mergeId ? keepId : id);
                }
            });
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
        const data = {
            persons: this.app.persons,
            events: this.app.events,
            relationships: this.app.relationships,
            metadata: {
                total_persons: Object.keys(this.app.persons).length,
                total_events: Object.keys(this.app.events).length,
                total_relationships: Object.keys(this.app.relationships).length,
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
                console.log('✓ Data saved to data/genealogy_complete.json');
            } else {
                console.error('Failed to save data:', response.statusText);
            }
        } catch (error) {
            console.error('Error saving data:', error);
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
