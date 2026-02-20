// Enrichment Review Module
class EnrichmentReviewer {
    constructor(app) {
        this.app = app;
        this.queue = null;
        this.currentIndex = 0;
        this.decisions = {};
    }

    async loadQueue() {
        try {
            const response = await fetch('../data/enrichment_queue.json');
            this.queue = await response.json();

            // Update button count
            const count = this.queue.matches ? this.queue.matches.length : 0;
            document.getElementById('enrichment-count').textContent = `(${count})`;

            return true;
        } catch (error) {
            console.error('Error loading enrichment queue:', error);
            return false;
        }
    }

    async open() {
        if (!this.queue) {
            const loaded = await this.loadQueue();
            if (!loaded || !this.queue.matches || this.queue.matches.length === 0) {
                alert('No enrichment queue found. Please run generate_enrichment_queue.py first.');
                return;
            }
        }

        this.currentIndex = 0;
        this.showModal();
        this.renderCurrent();
    }

    showModal() {
        document.getElementById('enrichment-modal').style.display = 'block';
    }

    close() {
        document.getElementById('enrichment-modal').style.display = 'none';
    }

    renderCurrent() {
        if (!this.queue || !this.queue.matches) return;

        const match = this.queue.matches[this.currentIndex];
        if (!match) return;

        const content = document.getElementById('enrichment-content');

        // Progress bar
        const progress = ((this.currentIndex + 1) / this.queue.matches.length) * 100;

        let html = `
            <div class="enrichment-progress">
                <span>${this.currentIndex + 1} of ${this.queue.matches.length}</span>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
                <span>${Math.round(progress)}%</span>
            </div>
        `;

        html += this.renderMatch(match);

        content.innerHTML = html;

        // Add event listeners
        this.attachEventListeners(match);
    }

    renderMatch(match) {
        const confidenceClass = match.confidence >= 85 ? 'confidence-high' : 'confidence-medium';
        const confidenceText = match.confidence >= 85 ? 'High' : 'Medium';

        let html = `
            <div class="enrichment-match">
                <div class="match-header">
                    <div class="match-title">${match.base_person.name}</div>
                    <div class="confidence-badge ${confidenceClass}">
                        ${confidenceText} Confidence (${match.confidence}%)
                    </div>
                </div>
        `;

        // Comparison section
        html += `
            <div class="comparison-section">
                <div class="comparison-panel">
                    <h4>📁 Your Data (base.md)</h4>
                    ${this.renderPersonData(match.base_person)}
                </div>
                <div class="comparison-panel">
                    <h4>📦 GEDCOM Data (base.ged)</h4>
                    ${this.renderPersonData(match.gedcom_person, true)}
                </div>
            </div>
        `;

        // Personal data imports
        if (Object.keys(match.personal_data_imports || {}).length > 0) {
            html += this.renderPersonalDataImports(match);
        }

        // Parents
        if (match.parents && match.parents.length > 0) {
            html += this.renderParents(match);
        }

        // Children
        if (match.children && match.children.length > 0) {
            html += this.renderChildren(match);
        }

        // Actions
        html += `
            <div class="enrichment-actions">
                <button class="btn-secondary" onclick="enrichmentReviewer.skip()">Skip This Match</button>
                <button class="btn-primary" onclick="enrichmentReviewer.apply()">Apply Changes</button>
            </div>
        `;

        html += `</div>`;

        return html;
    }

    renderPersonData(person, isGedcom = false) {
        let html = '';

        html += `<div class="data-row">
            <span class="data-label">Name:</span>
            <span class="data-value">${person.name}</span>
        </div>`;

        // Handle both date objects and simple year values
        const birthValue = person.birth_date ?
            (typeof person.birth_date === 'object' ? this.app.formatFlexibleDate(person.birth_date) : person.birth_date) :
            (person.birth_year || '?');
        const birthClass = isGedcom && person.birth_date ? 'new-data' : '';
        html += `<div class="data-row">
            <span class="data-label">Birth:</span>
            <span class="data-value ${birthClass}">${birthValue}</span>
        </div>`;

        const deathValue = person.death_date ?
            (typeof person.death_date === 'object' ? this.app.formatFlexibleDate(person.death_date) : person.death_date) :
            (person.death_year || '?');
        const deathClass = isGedcom && person.death_date ? 'new-data' : '';
        html += `<div class="data-row">
            <span class="data-label">Death:</span>
            <span class="data-value ${deathClass}">${deathValue}</span>
        </div>`;

        html += `<div class="data-row">
            <span class="data-label">Gender:</span>
            <span class="data-value">${person.gender || '?'}</span>
        </div>`;

        return html;
    }

    renderPersonalDataImports(match) {
        const imports = match.personal_data_imports;

        let html = `
            <div class="import-section">
                <h4>📝 Personal Data to Import:</h4>
        `;

        if (imports.birth_year) {
            html += `
                <div class="import-checkbox">
                    <input type="checkbox" id="import-birth" checked>
                    <label for="import-birth">Add birth year: ${imports.birth_year}</label>
                </div>
            `;
        }

        if (imports.death_year) {
            html += `
                <div class="import-checkbox">
                    <input type="checkbox" id="import-death" checked>
                    <label for="import-death">Add death year: ${imports.death_year}</label>
                </div>
            `;
        }

        html += `</div>`;

        return html;
    }

    renderParents(match) {
        let html = `
            <div class="relatives-section">
                <h3>👨‍👩 Parents (${match.parents.length})</h3>
        `;

        match.parents.forEach((parent, index) => {
            html += this.renderRelative(parent, 'parent', index);
        });

        html += `</div>`;

        return html;
    }

    renderChildren(match) {
        let html = `
            <div class="relatives-section">
                <h3>👶 Children (${match.children.length})</h3>
        `;

        match.children.forEach((child, index) => {
            html += this.renderRelative(child, 'child', index);
        });

        html += `</div>`;

        return html;
    }

    renderRelative(relative, type, index) {
        const name = `${relative.given_name} ${relative.surname}`;
        const years = `${relative.birth_year || '?'}-${relative.death_year || '?'}`;
        const hasMatches = relative.matches && relative.matches.length > 0;

        let html = `
            <div class="relative-item">
                <div class="relative-header">
                    <div class="relative-name">${name} (${years})</div>
                </div>
        `;

        if (hasMatches) {
            html += `<div class="match-options">`;

            // Show matches
            relative.matches.forEach((match, matchIndex) => {
                const person = this.app.persons[match.person_id];

                // Skip if person not found (shouldn't happen, but defensive coding)
                if (!person) {
                    console.error(`Person ${match.person_id} not found in app.persons`);
                    return;
                }

                const optionClass = match.recommended ? 'match-option recommended' : 'match-option';
                const checked = matchIndex === 0 && match.recommended ? 'checked' : '';

                html += `
                    <div class="${optionClass}">
                        <input type="radio"
                               name="${type}-${index}"
                               id="${type}-${index}-match-${matchIndex}"
                               value="merge:${match.person_id}"
                               ${checked}>
                        <label for="${type}-${index}-match-${matchIndex}">
                            <strong>MERGE</strong> with ${this.app.getFullName(person)}
                            <span class="match-score">${match.score}%</span>
                            ${match.recommended ? ' ⭐' : ''}
                        </label>
                        ${this.renderMatchEvidence(match)}
                        ${match.would_add.length > 0 ? `
                            <div style="margin-top: 8px; padding-left: 30px; font-size: 0.9rem; color: #27ae60;">
                                Will add: ${match.would_add.join(', ')}
                            </div>
                        ` : ''}
                    </div>
                `;
            });

            // "Create new" option
            const createChecked = !hasMatches || !relative.matches.some(m => m.recommended) ? 'checked' : '';
            html += `
                <div class="match-option">
                    <input type="radio"
                           name="${type}-${index}"
                           id="${type}-${index}-create"
                           value="create"
                           ${createChecked}>
                    <label for="${type}-${index}-create">
                        <strong>CREATE NEW</strong> person as ${relative.create_new_option.would_create_id}
                    </label>
                </div>
            `;

            html += `</div>`;
        } else {
            // No matches, only create new option
            html += `
                <div class="match-options">
                    <div class="match-option">
                        <input type="radio"
                               name="${type}-${index}"
                               id="${type}-${index}-create"
                               value="create"
                               checked>
                        <label for="${type}-${index}-create">
                            <strong>CREATE NEW</strong> person as ${relative.create_new_option.would_create_id}
                        </label>
                        <div style="margin-top: 8px; padding-left: 30px; font-size: 0.9rem; color: #666;">
                            No existing matches found
                        </div>
                    </div>
                </div>
            `;
        }

        html += `</div>`;

        return html;
    }

    renderMatchEvidence(match) {
        if (!match.evidence || match.evidence.length === 0) return '';

        let html = `<ul class="match-evidence">`;
        match.evidence.forEach(evidence => {
            html += `<li>${evidence}</li>`;
        });
        html += `</ul>`;

        return html;
    }

    attachEventListeners(match) {
        // Add listeners for radio buttons to highlight selected options
        document.querySelectorAll('.match-option').forEach(option => {
            const radio = option.querySelector('input[type="radio"]');
            if (radio) {
                radio.addEventListener('change', () => {
                    // Remove highlight from siblings
                    option.parentElement.querySelectorAll('.match-option').forEach(o => {
                        o.style.borderColor = '#e0e0e0';
                        o.style.background = '#f8f9fa';
                    });

                    // Highlight selected
                    if (radio.checked) {
                        option.style.borderColor = '#667eea';
                        option.style.background = '#f0f4ff';
                    }
                });
            }
        });
    }

    async apply() {
        const match = this.queue.matches[this.currentIndex];

        // Collect decisions
        const decision = {
            match_id: match.match_id,
            base_person_id: match.base_person.id,
            personal_data: {},
            parents: [],
            children: []
        };

        // Personal data imports
        if (document.getElementById('import-birth')?.checked) {
            decision.personal_data.birth_year = match.personal_data_imports.birth_year;
        }
        if (document.getElementById('import-death')?.checked) {
            decision.personal_data.death_year = match.personal_data_imports.death_year;
        }

        // Parents
        match.parents?.forEach((parent, index) => {
            const selected = document.querySelector(`input[name="parent-${index}"]:checked`);
            if (selected) {
                const value = selected.value;
                if (value.startsWith('merge:')) {
                    decision.parents.push({
                        action: 'merge',
                        gedcom_id: parent.gedcom_id,
                        merge_with: value.split(':')[1],
                        relationship: parent.relationship
                    });
                } else {
                    decision.parents.push({
                        action: 'create',
                        gedcom_id: parent.gedcom_id,
                        relationship: parent.relationship,
                        data: {
                            given_name: parent.given_name,
                            surname: parent.surname,
                            maiden_name: parent.maiden_name,
                            birth_year: parent.birth_year,
                            death_year: parent.death_year,
                            gender: parent.gender
                        }
                    });
                }
            }
        });

        // Children
        match.children?.forEach((child, index) => {
            const selected = document.querySelector(`input[name="child-${index}"]:checked`);
            if (selected) {
                const value = selected.value;
                if (value.startsWith('merge:')) {
                    decision.children.push({
                        action: 'merge',
                        gedcom_id: child.gedcom_id,
                        merge_with: value.split(':')[1]
                    });
                } else {
                    decision.children.push({
                        action: 'create',
                        gedcom_id: child.gedcom_id,
                        data: {
                            given_name: child.given_name,
                            surname: child.surname,
                            birth_year: child.birth_year,
                            death_year: child.death_year,
                            gender: child.gender
                        }
                    });
                }
            }
        });

        // Apply changes via API
        try {
            const response = await fetch('/api/apply-enrichment', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(decision)
            });

            const result = await response.json();

            if (result.success) {
                // Reload data
                await this.app.loadData();
                this.app.createNetwork();
                this.app.updateStats();

                // Move to next or close
                this.next();
            } else {
                alert('Error applying changes: ' + result.error);
            }
        } catch (error) {
            console.error('Error applying enrichment:', error);
            alert('Error applying changes. Check console for details.');
        }
    }

    skip() {
        this.next();
    }

    next() {
        this.currentIndex++;

        if (this.currentIndex >= this.queue.matches.length) {
            alert('All matches reviewed!');
            this.close();
            // Reload queue to get updated count
            this.queue = null;
            this.loadQueue();
        } else {
            this.renderCurrent();
        }
    }
}

// Initialize when app is ready
let enrichmentReviewer = null;

// Will be called from app.js after app initialization
function initEnrichmentReviewer(app) {
    enrichmentReviewer = new EnrichmentReviewer(app);
    enrichmentReviewer.loadQueue();
}
