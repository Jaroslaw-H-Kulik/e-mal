// Genealogical Database Application
class GenealogyApp {
    constructor() {
        this.persons = {};
        this.events = {};
        this.places = {};
        this.event_participations = {};
        this.network = null;
        this.currentView = 'all';
        this.selectedPerson = null;

        // Performance: caches and indices
        this.relationshipCache = new Map();
        this.validationCache = new Map();
        this.participationsByPerson = {};
        this.participationsByEvent = {};

        this.init();
    }

    // Date formatting helpers
    formatFlexibleDate(dateObj) {
        if (!dateObj) return '?';
        const prefix = dateObj.circa ? 'circa ' : '';
        if (dateObj.day && dateObj.month && dateObj.year) {
            return `${prefix}${dateObj.day}/${dateObj.month}/${dateObj.year}`;
        } else if (dateObj.month && dateObj.year) {
            return `${prefix}${dateObj.month}/${dateObj.year}`;
        } else if (dateObj.year) {
            return `${prefix}${dateObj.year}`;
        }
        return '?';
    }

    extractYear(dateObj) {
        return dateObj?.year || null;
    }

    // Person name helper
    getFullName(person) {
        return `${person.first_name || ''} ${person.last_name || ''}`.trim();
    }

    // Person name with maiden name helper
    getFullNameWithMaiden(person) {
        const fullName = this.getFullName(person);
        if (person.maiden_name) {
            return `${fullName} (née ${person.maiden_name})`;
        }
        return fullName;
    }

    async init() {
        await this.loadData();
        this.setupUI();
        this.setupEventListeners();
        this.createNetwork();
        this.updateStats();
        this.hideLoading();

        // Handle URL-based person selection or default to P0264
        this.handleInitialPersonSelection();
    }

    async loadData() {
        try {
            // Load NEW model with cache-busting to ensure fresh data
            const response = await fetch(`../data/genealogy_new_model.json?t=${Date.now()}`);
            const data = await response.json();

            // Update data structure references
            this.persons = data.persons;
            this.places = data.places || {};
            this.events = data.events;
            this.event_participations = data.event_participations || {};

            console.log('Data loaded:', {
                persons: Object.keys(this.persons).length,
                places: Object.keys(this.places).length,
                events: Object.keys(this.events).length,
                event_participations: Object.keys(this.event_participations).length
            });

            // Performance: Build indices for fast lookups
            this.buildIndices();
        } catch (error) {
            console.error('Error loading data:', error);
            alert('Error loading genealogical data. Please ensure the data files are in the correct location.');
        }
    }

    buildIndices() {
        // Build index of participations by person
        this.participationsByPerson = {};
        this.participationsByEvent = {};

        Object.entries(this.event_participations).forEach(([id, ep]) => {
            // Index by person
            if (!this.participationsByPerson[ep.person_id]) {
                this.participationsByPerson[ep.person_id] = [];
            }
            this.participationsByPerson[ep.person_id].push(ep);

            // Index by event
            if (!this.participationsByEvent[ep.event_id]) {
                this.participationsByEvent[ep.event_id] = [];
            }
            this.participationsByEvent[ep.event_id].push(ep);
        });

        console.log('Indices built');
    }

    setupUI() {
        // Populate surname filter
        const surnames = new Set();
        Object.values(this.persons).forEach(person => {
            if (person.last_name && person.last_name !== 'Unknown') {
                surnames.add(person.last_name);
            }
        });

        const surnameSelect = document.getElementById('surname-select');
        Array.from(surnames).sort().forEach(surname => {
            const option = document.createElement('option');
            option.value = surname;
            option.textContent = surname;
            surnameSelect.appendChild(option);
        });

        // Enable/disable surname select based on checkbox
        document.getElementById('filter-surname').addEventListener('change', (e) => {
            document.getElementById('surname-select').disabled = !e.target.checked;
        });
    }

    setupEventListeners() {
        // Handle browser back/forward buttons
        window.addEventListener('popstate', () => {
            const urlParams = new URLSearchParams(window.location.search);
            const personId = urlParams.get('person');
            if (personId && this.persons[personId]) {
                // Pass false to not update URL during popstate
                this.showPersonDetails(personId, false);
                this.network.selectNodes([personId]);
                this.network.focus(personId, { scale: 1.5, animation: true });
            }
        });

        // Search
        document.getElementById('search-btn').addEventListener('click', () => this.handleSearch());
        document.getElementById('search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleSearch();
        });

        // Reset view
        document.getElementById('reset-btn').addEventListener('click', () => this.resetView());

        // View controls
        document.getElementById('view-all-btn').addEventListener('click', () => this.changeView('all'));
        document.getElementById('view-families-btn').addEventListener('click', () => this.changeView('families'));
        document.getElementById('view-marriages-btn').addEventListener('click', () => this.changeView('marriages'));
        document.getElementById('view-godparents-btn').addEventListener('click', () => this.changeView('godparents'));
        document.getElementById('view-witnesses-btn').addEventListener('click', () => this.changeView('witnesses'));

        // Filters
        document.getElementById('apply-filters-btn').addEventListener('click', () => this.applyFilters());

        // Close details
        document.getElementById('close-details-btn').addEventListener('click', () => this.closeDetails());

        // Click outside to collapse search filters
        document.addEventListener('click', (e) => {
            const filtersSection = document.getElementById('search-filters-section');
            const searchInput = document.getElementById('search-input');

            if (filtersSection && filtersSection.style.display === 'block') {
                // Check if click is outside both the filters section and search input
                if (!filtersSection.contains(e.target) && e.target !== searchInput && !searchInput.contains(e.target)) {
                    this.collapseSearchFilters();
                }
            }
        });
    }

    createNetwork() {
        const container = document.getElementById('network-container');

        // Prepare nodes (persons)
        const nodes = [];
        Object.entries(this.persons).forEach(([id, person]) => {
            const birthYear = this.extractYear(person.birth_date);
            const deathYear = this.extractYear(person.death_date);
            const yearsLabel = birthYear || deathYear ? `\n(${birthYear || '?'}-${deathYear || '?'})` : '';

            nodes.push({
                id: id,
                label: `${this.getFullName(person)}${yearsLabel}`,
                title: this.getPersonTooltip(id, person),
                color: this.getPersonColor(person.gender),
                font: {
                    size: 14,
                    color: '#333'
                },
                borderWidth: 2,
                borderWidthSelected: 4
            });
        });

        // Prepare edges from events
        const edges = [];
        const edgeSet = new Set(); // Track unique edges to avoid duplicates

        // Process all events to extract relationships
        Object.values(this.events).forEach(event => {
            const participants = Object.values(this.event_participations)
                .filter(ep => ep.event_id === event.id);

            if (event.type === 'birth') {
                // Extract parent-child relationships
                const child = participants.find(p => p.role === 'child');
                const parents = participants.filter(p => p.role === 'father' || p.role === 'mother');

                if (child) {
                    parents.forEach(parent => {
                        const edgeKey = `parent-${parent.person_id}-${child.person_id}`;
                        if (!edgeSet.has(edgeKey)) {
                            edgeSet.add(edgeKey);
                            edges.push({
                                from: parent.person_id,
                                to: child.person_id,
                                arrows: this.getEdgeArrows('biological_parent'),
                                color: this.getEdgeColor('biological_parent'),
                                width: 2,
                                smooth: {
                                    type: 'curvedCW',
                                    roundness: 0.2
                                },
                                relType: 'biological_parent',
                                title: `Parent of`
                            });
                        }
                    });
                }
            } else if (event.type === 'marriage') {
                // Extract spouse relationships
                const spouses = participants.filter(p => p.role === 'groom' || p.role === 'bride');
                if (spouses.length === 2) {
                    const edgeKey = `spouse-${spouses[0].person_id}-${spouses[1].person_id}`;
                    const reverseKey = `spouse-${spouses[1].person_id}-${spouses[0].person_id}`;
                    if (!edgeSet.has(edgeKey) && !edgeSet.has(reverseKey)) {
                        edgeSet.add(edgeKey);
                        edges.push({
                            from: spouses[0].person_id,
                            to: spouses[1].person_id,
                            arrows: this.getEdgeArrows('marriage'),
                            color: this.getEdgeColor('marriage'),
                            width: 2,
                            smooth: {
                                type: 'curvedCW',
                                roundness: 0.2
                            },
                            relType: 'marriage',
                            title: `Married to`
                        });
                    }
                }
            }
        });

        // Build map of event participations for quick lookup
        const eventParticipationsByEvent = {};
        Object.values(this.event_participations).forEach(ep => {
            if (!eventParticipationsByEvent[ep.event_id]) {
                eventParticipationsByEvent[ep.event_id] = [];
            }
            eventParticipationsByEvent[ep.event_id].push(ep);
        });

        // Add witness relationships from events using participations
        const witnessConnections = new Set(); // Avoid duplicates
        Object.entries(this.events).forEach(([eventId, event]) => {
            const participants = eventParticipationsByEvent[eventId] || [];

            // Find witnesses and main participants
            const witnesses = participants.filter(ep => ep.role === 'witness');
            const mainParticipants = participants.filter(ep =>
                ['child', 'deceased', 'groom', 'bride'].includes(ep.role)
            );

            // Connect witnesses to main participants
            witnesses.forEach(witness => {
                mainParticipants.forEach(mainPart => {
                    if (witness.person_id !== mainPart.person_id) {
                        // Create unique key to avoid duplicates
                        const key = `${witness.person_id}-${mainPart.person_id}`;
                        if (!witnessConnections.has(key)) {
                            witnessConnections.add(key);
                            edges.push({
                                from: witness.person_id,
                                to: mainPart.person_id,
                                arrows: '',
                                color: { color: '#95a5a6', opacity: 0.5 },
                                width: 1,
                                dashes: [5, 5],
                                smooth: {
                                    type: 'curvedCW',
                                    roundness: 0.3
                                },
                                relType: 'witness',
                                title: 'Witnessed event together'
                            });
                        }
                    }
                });
            });
        });

        // Network options
        const options = {
            nodes: {
                shape: 'dot',
                size: 16,
                font: {
                    size: 12
                }
            },
            edges: {
                smooth: {
                    enabled: true,
                    type: 'dynamic'
                }
            },
            physics: {
                enabled: true,
                stabilization: {
                    iterations: 200
                },
                barnesHut: {
                    gravitationalConstant: -8000,
                    centralGravity: 0.3,
                    springLength: 150,
                    springConstant: 0.04,
                    damping: 0.09
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 100,
                navigationButtons: true,
                keyboard: true
            }
        };

        // Create network
        const data = { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) };
        this.network = new vis.Network(container, data, options);

        // Handle click events
        this.network.on('click', (params) => {
            console.log('Network clicked:', params);
            if (params.nodes.length > 0) {
                const personId = params.nodes[0];
                console.log('Person clicked:', personId);
                try {
                    this.showPersonDetails(personId);
                    this.focusOnPersonNetwork(personId);
                } catch (error) {
                    console.error('Error showing person details:', error);
                    alert(`Error displaying person ${personId}: ${error.message}`);
                }
            } else {
                console.log('Clicked on empty space - showing full network');
                this.showFullNetwork();
            }
        });

        // Handle double click to focus
        this.network.on('doubleClick', (params) => {
            if (params.nodes.length > 0) {
                const personId = params.nodes[0];
                this.focusOnPerson(personId);
            }
        });
    }

    getPersonColor(gender) {
        switch(gender) {
            case 'M': return { background: '#4A90E2', border: '#2E5C8A' };
            case 'F': return { background: '#E94B8B', border: '#A73264' };
            default: return { background: '#95A5A6', border: '#6C7A7B' };
        }
    }

    getEdgeColor(relType) {
        switch(relType) {
            case 'biological_parent': return { color: '#2ecc71', highlight: '#27ae60' };
            case 'marriage': return { color: '#e74c3c', highlight: '#c0392b' };
            case 'godparent': return { color: '#f39c12', highlight: '#d68910' };
            default: return { color: '#95a5a6', highlight: '#7f8c8d' };
        }
    }

    getEdgeArrows(relType) {
        if (relType === 'biological_parent') {
            return { to: { enabled: true, scaleFactor: 0.5 } };
        }
        return undefined;
    }

    getRelationshipLabel(rel) {
        const labels = {
            'biological_parent': `Parent: ${rel.role || 'parent'}`,
            'marriage': 'Marriage',
            'godparent': 'Godparent'
        };
        return labels[rel.type] || rel.type;
    }

    getPersonTooltip(id, person) {
        const birthYear = this.extractYear(person.birth_date);
        const deathYear = this.extractYear(person.death_date);
        const birth = birthYear ? `b. ${birthYear}` : '';
        const death = deathYear ? `d. ${deathYear}` : '';
        const years = [birth, death].filter(Boolean).join(', ');

        let tooltip = `<b>${this.getFullName(person)}</b><br>`;
        tooltip += `ID: ${id}<br>`;
        if (years) tooltip += `${years}<br>`;
        if (person.maiden_name) tooltip += `Maiden: ${person.maiden_name}<br>`;
        if (person.occupation) {
            tooltip += `Occupation: ${person.occupation}`;
        }

        return tooltip;
    }

    handleSearch() {
        const query = document.getElementById('search-input').value.trim().toLowerCase();
        if (!query) return;

        const results = [];
        Object.entries(this.persons).forEach(([id, person]) => {
            const fullName = this.getFullName(person).toLowerCase();
            const idMatch = id.toLowerCase().includes(query);
            const nameMatch = fullName.includes(query);
            const surnameMatch = person.last_name ? person.last_name.toLowerCase().includes(query) : false;

            if (idMatch || nameMatch || surnameMatch) {
                results.push({ id, person });
            }
        });

        this.displaySearchResults(results);
    }

    displaySearchResults(results) {
        const container = document.getElementById('search-results');
        container.innerHTML = '';

        if (results.length === 0) {
            container.innerHTML = '<div class="search-result-item"><p>No results found</p></div>';
            return;
        }

        results.forEach(({ id, person }) => {
            const item = document.createElement('div');
            item.className = 'search-result-item';

            const birth = this.extractYear(person.birth_date) || '?';
            const death = this.extractYear(person.death_date) || '?';
            const gender = person.gender === 'M' ? '♂' : person.gender === 'F' ? '♀' : '?';

            item.innerHTML = `
                <div class="result-name">${this.getFullName(person)} ${gender}</div>
                <div class="result-info">
                    ${id} • ${birth}-${death}
                    ${person.maiden_name ? `• maiden: ${person.maiden_name}` : ''}
                </div>
            `;

            item.addEventListener('click', () => {
                this.showPersonDetails(id);
                this.network.selectNodes([id]);
                this.network.focus(id, {
                    scale: 1.5,
                    animation: {
                        duration: 1000,
                        easingFunction: 'easeInOutQuad'
                    }
                });
            });

            container.appendChild(item);
        });
    }

    showPersonDetails(personId, updateUrl = true) {
        console.log('showPersonDetails called with:', personId);
        this.selectedPerson = personId;

        // Performance: Clear caches when switching persons
        this.relationshipCache.clear();
        this.validationCache.clear();
        if (this.familyCache) this.familyCache.clear();

        // Update URL with person ID (unless we're handling back/forward)
        if (updateUrl) {
            const url = new URL(window.location);
            url.searchParams.set('person', personId);
            window.history.pushState({}, '', url);
        }

        const person = this.persons[personId];
        console.log('Person data:', person);

        if (!person) {
            console.error('Person not found:', personId);
            alert(`Person ${personId} not found in database`);
            return;
        }

        const detailsContainer = document.getElementById('person-details');
        document.getElementById('close-details-btn').style.display = 'block';

        // Build HTML
        let html = `
            <div class="person-header">
                <div class="person-name">
                    ${this.getFullName(person)}
                </div>
                <div class="person-id">${personId}</div>
                ${person.maiden_name ? `<div style="margin-top: 8px; color: #666;">née ${person.maiden_name}</div>` : ''}
                <div class="person-dates">
                    ${person.birth_date ? `Born: ${this.formatFlexibleDate(person.birth_date)}` : ''}
                    ${person.death_date ? `<br>Died: ${this.formatFlexibleDate(person.death_date)}` : ''}
                </div>
                <div style="margin-top: 10px;">
                    ${this.getGenderBadge(person.gender)}
                    ${person.occupation ? `<span class="badge">${person.occupation}</span>` : ''}
                </div>
                <div class="person-actions">
                    <button class="btn-primary" onclick="editor.openEditModal('${personId}')">✏️ Edit</button>
                    <button class="btn-success" onclick="editor.selectPersonForMerge('${personId}')">🔗 Select for Merge</button>
                    <button class="btn-danger" onclick="genealogyApp.deletePerson('${personId}')">🗑️ Delete</button>
                </div>
            </div>
        `;

        // Family section
        const family = this.getFamily(personId);
        if (family.parents.length > 0 || family.children.length > 0 || family.spouses.length > 0 || family.siblings.length > 0) {
            html += '<div class="detail-section"><div class="section-title">👨‍👩‍👧‍👦 Family</div>';

            if (family.parents.length > 0) {
                html += '<div class="detail-item">';
                html += '<div class="detail-label">Parents</div>';
                family.parents.forEach(p => {
                    const parent = this.persons[p.id];
                    html += `<div><a href="#" class="person-link" data-person-id="${p.id}">
                        ${this.getFullNameWithMaiden(parent)} (${p.role})
                    </a></div>`;
                });
                html += '</div>';
            }

            if (family.spouses.length > 0) {
                html += '<div class="detail-item">';
                html += '<div class="detail-label">Spouse(s)</div>';
                family.spouses.forEach(spouseId => {
                    const spouse = this.persons[spouseId];
                    html += `<div><a href="#" class="person-link" data-person-id="${spouseId}">
                        ${this.getFullNameWithMaiden(spouse)}
                    </a></div>`;
                });
                html += '</div>';
            }

            if (family.children.length > 0) {
                html += '<div class="detail-item">';
                html += `<div class="detail-label">Children (${family.children.length})</div>`;
                family.children.forEach(childId => {
                    const child = this.persons[childId];
                    const birthYear = this.extractYear(child.birth_date) || '?';
                    html += `<div><a href="#" class="person-link" data-person-id="${childId}">
                        ${this.getFullNameWithMaiden(child)} (b. ${birthYear})
                    </a></div>`;
                });
                html += '</div>';
            }

            if (family.siblings.length > 0) {
                html += '<div class="detail-item">';
                html += `<div class="detail-label">Siblings (${family.siblings.length})</div>`;
                family.siblings.forEach(siblingId => {
                    const sibling = this.persons[siblingId];
                    html += `<div><a href="#" class="person-link" data-person-id="${siblingId}">
                        ${this.getFullNameWithMaiden(sibling)}
                    </a></div>`;
                });
                html += '</div>';
            }

            html += '</div>';
        }

        // Godparents & Godchildren section
        const godrelations = this.getGodrelations(personId);
        if (godrelations.godparents.length > 0 || godrelations.godchildren.length > 0) {
            html += '<div class="detail-section"><div class="section-title">🕊️ Godparents & Godchildren</div>';

            if (godrelations.godparents.length > 0) {
                html += '<div class="detail-item">';
                html += `<div class="detail-label">Godparents (${godrelations.godparents.length})</div>`;
                godrelations.godparents.forEach(godparentId => {
                    const godparent = this.persons[godparentId];
                    html += `<div><a href="#" class="person-link" data-person-id="${godparentId}">
                        ${this.getFullNameWithMaiden(godparent)}
                    </a></div>`;
                });
                html += '</div>';
            }

            if (godrelations.godchildren.length > 0) {
                html += '<div class="detail-item">';
                html += `<div class="detail-label">Godchildren (${godrelations.godchildren.length})</div>`;
                godrelations.godchildren.forEach(godchildId => {
                    const godchild = this.persons[godchildId];
                    const birthYear = this.extractYear(godchild.birth_date) || '?';
                    html += `<div><a href="#" class="person-link" data-person-id="${godchildId}">
                        ${this.getFullNameWithMaiden(godchild)} (b. ${birthYear})
                    </a></div>`;
                });
                html += '</div>';
            }

            html += '</div>';
        }

        // Events section
        const events = this.getPersonEvents(personId);
        html += '<div class="detail-section">';
        html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">';
        html += '<div class="section-title">📅 Events</div>';
        html += `<button class="btn-primary" style="padding: 6px 12px; font-size: 0.85rem;" onclick="eventEditor.openAddEventModal('${personId}')">+ Add Event</button>`;
        html += '</div>';
        if (events.length > 0) {
            events.forEach(event => {
                const year = event.date?.year || '?';
                const eventContent = event.content || event.original_text || 'No content available';
                const eventId = event.id;

                // Get current person's role in this event
                let personRoleHTML = '';
                const personParticipation = Object.values(this.event_participations).find(
                    ep => ep.event_id === eventId && ep.person_id === personId
                );

                if (personParticipation) {
                    const role = personParticipation.role;
                    const person = this.persons[personId];
                    const birthYear = this.extractYear(person.birth_date);
                    const eventYear = event.date?.year;

                    let roleInfo = `Role: <strong>${role}</strong>`;

                    if (birthYear && eventYear) {
                        const age = eventYear - birthYear;
                        roleInfo += `, Age: <strong>${age}</strong>`;
                    }

                    personRoleHTML = `<div style="margin-top: 8px; padding: 6px 8px; background: #e8f4f8; border-left: 3px solid #667eea; border-radius: 3px; font-size: 0.9rem;">
                        ${roleInfo}
                    </div>`;
                }

                // Step 23: Check for validation issues
                const validationWarning = this.hasEventValidationIssue(eventId, personId) ? ' <span style="color: red; font-weight: bold;" title="Data issue detected">!</span>' : '';

                html += `
                    <div class="event-item expandable-event" data-event-id="${eventId}">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div class="event-header" onclick="app.toggleEventDetails('${eventId}')" style="flex: 1;">
                                <div style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
                                    <span class="event-expand-icon" id="expand-icon-${eventId}">▶</span>
                                    <div class="event-year">${year}${validationWarning}</div>
                                    <span class="event-type">${event.type}</span>
                                </div>
                            </div>
                            <button class="btn-secondary" style="padding: 4px 8px; font-size: 0.75rem; margin-right: 4px;" onclick="event.stopPropagation(); eventEditor.openEditEventModal('${eventId}')">Edit</button>
                            <button class="btn-danger" style="padding: 4px 8px; font-size: 0.75rem;" onclick="event.stopPropagation(); genealogyApp.deleteEvent('${eventId}')">Delete</button>
                        </div>
                        <div class="event-text" onclick="app.toggleEventDetails('${eventId}')" style="cursor: pointer;">
                            ${eventContent}
                        </div>
                        ${personRoleHTML}
                        <div class="event-participants" id="participants-${eventId}" style="display: none; margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 4px;">
                            ${this.getEventParticipantsHTML(eventId)}
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        }

        detailsContainer.innerHTML = html;

        // Add click handlers for person links (family and participants)
        detailsContainer.querySelectorAll('.person-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('data-person-id');
                if (targetId) {
                    this.showPersonDetails(targetId);
                    this.network.selectNodes([targetId]);
                    this.network.focus(targetId, { scale: 1.5, animation: true });
                }
            });
        });
    }

    getGenderBadge(gender) {
        if (gender === 'M') return '<span class="badge male">♂ Male</span>';
        if (gender === 'F') return '<span class="badge female">♀ Female</span>';
        return '<span class="badge">? Unknown</span>';
    }

    getFamily(personId) {
        // Performance: Cache family results
        if (this.familyCache && this.familyCache.has(personId)) {
            return this.familyCache.get(personId);
        }
        if (!this.familyCache) {
            this.familyCache = new Map();
        }

        const family = {
            parents: [],
            children: [],
            spouses: [],
            siblings: []
        };

        // Performance: Use participationsByPerson index instead of iterating all
        const personParticipations = this.participationsByPerson[personId] || [];

        personParticipations.forEach(ep => {
            const event = this.events[ep.event_id];
            if (!event) return;

            // Birth events contain parent-child relationships
            if (event.type === 'birth') {
                // Performance: Use participationsByEvent index
                const participants = this.participationsByEvent[ep.event_id] || [];

                const child = participants.find(p => p.role === 'child');
                const fathers = participants.filter(p => p.role === 'father');
                const mothers = participants.filter(p => p.role === 'mother');

                if (child && child.person_id === personId) {
                    // This person is the child - collect parents
                    fathers.forEach(f => {
                        if (!family.parents.find(p => p.id === f.person_id)) {
                            family.parents.push({
                                id: f.person_id,
                                role: 'father'
                            });
                        }
                    });
                    mothers.forEach(m => {
                        if (!family.parents.find(p => p.id === m.person_id)) {
                            family.parents.push({
                                id: m.person_id,
                                role: 'mother'
                            });
                        }
                    });
                } else if (ep.person_id === personId && (ep.role === 'father' || ep.role === 'mother')) {
                    // This person is a parent - collect children
                    if (child && !family.children.includes(child.person_id)) {
                        family.children.push(child.person_id);
                    }
                }
            }

            // Marriage events contain spouse relationships
            if (event.type === 'marriage' && ep.person_id === personId) {
                // Performance: Use participationsByEvent index
                const participants = (this.participationsByEvent[ep.event_id] || [])
                    .filter(e => e.role === 'groom' || e.role === 'bride');

                participants.forEach(p => {
                    if (p.person_id !== personId && !family.spouses.includes(p.person_id)) {
                        family.spouses.push(p.person_id);
                    }
                });
            }
        });

        // Find siblings: people who share the same parents
        const parentIds = family.parents.map(p => p.id);
        if (parentIds.length > 0) {
            // Performance: Use participationsByPerson index for each parent
            parentIds.forEach(parentId => {
                const parentParticipations = this.participationsByPerson[parentId] || [];
                parentParticipations.forEach(ep => {
                    if (ep.role === 'father' || ep.role === 'mother') {
                        const event = this.events[ep.event_id];
                        if (event && event.type === 'birth') {
                            // Performance: Use participationsByEvent index
                            const participants = this.participationsByEvent[ep.event_id] || [];
                            const child = participants.find(p => p.role === 'child');

                            if (child && child.person_id !== personId && !family.siblings.includes(child.person_id)) {
                                family.siblings.push(child.person_id);
                            }
                        }
                    }
                });
            });
        }

        // Cache the result
        this.familyCache.set(personId, family);
        return family;
    }

    getGodrelations(personId) {
        const godrelations = {
            godparents: [],
            godchildren: []
        };

        // Query event_participations instead of relationships
        Object.values(this.event_participations).forEach(ep => {
            // Find birth/baptism events where this person participated
            const event = this.events[ep.event_id];
            if (!event || (event.type !== 'birth' && event.type !== 'baptism')) {
                return;
            }

            // Get all participants of this event
            const eventParticipants = Object.values(this.event_participations)
                .filter(e => e.event_id === ep.event_id);

            // Find child and godparents in this event
            const child = eventParticipants.find(e => e.role === 'child');
            const godparents = eventParticipants.filter(e => e.role === 'godparent');

            // If current person is the child, collect godparents
            if (child && child.person_id === personId) {
                godparents.forEach(gp => {
                    if (!godrelations.godparents.includes(gp.person_id)) {
                        godrelations.godparents.push(gp.person_id);
                    }
                });
            }
            // If current person is a godparent, collect godchildren
            else if (ep.person_id === personId && ep.role === 'godparent') {
                if (child && !godrelations.godchildren.includes(child.person_id)) {
                    godrelations.godchildren.push(child.person_id);
                }
            }
        });

        return godrelations;
    }

    getPersonEvents(personId) {
        const events = [];
        const eventIds = new Set();

        // Find all events where this person participated
        Object.values(this.event_participations).forEach(ep => {
            if (ep.person_id === personId) {
                eventIds.add(ep.event_id);
            }
        });

        // Collect the actual event objects
        eventIds.forEach(eventId => {
            const event = this.events[eventId];
            if (event) {
                events.push(event);
            }
        });

        // Sort by year
        events.sort((a, b) => {
            const yearA = a.date?.year || 0;
            const yearB = b.date?.year || 0;
            return yearA - yearB;
        });
        return events;
    }

    getEventGodparents(eventId) {
        // Get all godparents for this event
        const godparents = Object.values(this.event_participations)
            .filter(ep => ep.event_id === eventId && ep.role === 'godparent')
            .map(ep => ep.person_id);
        return godparents;
    }

    getEventParticipantsHTML(eventId) {
        // Performance: Use index instead of filtering all participations
        const participants = this.participationsByEvent[eventId] || [];

        if (participants.length === 0) {
            return '<div style="color: #666; font-style: italic;">No participants recorded</div>';
        }

        // Get event date for age calculation
        const event = this.events[eventId];
        const eventYear = event?.date?.year;

        // Group participants by role
        const roleGroups = {};
        participants.forEach(ep => {
            const role = ep.role || 'unknown';
            if (!roleGroups[role]) {
                roleGroups[role] = [];
            }
            roleGroups[role].push(ep.person_id);
        });

        // Role display names without emojis
        const roleNames = {
            'child': 'Child',
            'father': 'Father',
            'mother': 'Mother',
            'groom': 'Groom',
            'bride': 'Bride',
            'deceased': 'Deceased',
            'witness': 'Witness',
            'godparent': 'Godparent',
            'unknown': 'Unknown'
        };

        let html = '<div style="font-weight: 600; margin-bottom: 8px;">Participants:</div>';

        // Display each role group
        Object.entries(roleGroups).forEach(([role, personIds]) => {
            const roleName = roleNames[role] || role;
            html += `<div style="margin-bottom: 6px;">
                <div style="font-weight: 500; color: #555; margin-bottom: 4px;">${roleName}:</div>
                <div style="padding-left: 15px;">`;

            personIds.forEach(personId => {
                const person = this.persons[personId];
                if (person) {
                    const birthYear = this.extractYear(person.birth_date);
                    let ageInfo = '';

                    if (birthYear && eventYear) {
                        const age = eventYear - birthYear;
                        ageInfo = ` (age ${age}, b. ${birthYear})`;
                    } else if (birthYear) {
                        ageInfo = ` (b. ${birthYear})`;
                    }

                    // Step 22: Add relationship info
                    let relationshipInfo = '';
                    if (this.selectedPerson && this.selectedPerson !== personId) {
                        const relationship = this.getRelationship(this.selectedPerson, personId);
                        if (relationship) {
                            relationshipInfo = ` - <em>${relationship}</em>`;
                        }
                    }

                    html += `
                        <div style="margin-bottom: 3px;">
                            <a href="#" class="person-link participant-link" data-person-id="${personId}"
                               style="color: #667eea; text-decoration: none; font-weight: 500;">
                                ${this.getFullName(person)}${ageInfo}${relationshipInfo}
                            </a>
                        </div>`;
                } else {
                    html += `<div style="color: #999;">Unknown person (${personId})</div>`;
                }
            });

            html += '</div></div>';
        });

        return html;
    }

    toggleEventDetails(eventId) {
        const participantsDiv = document.getElementById(`participants-${eventId}`);
        const expandIcon = document.getElementById(`expand-icon-${eventId}`);

        if (participantsDiv.style.display === 'none') {
            participantsDiv.style.display = 'block';
            expandIcon.textContent = '▼';
            expandIcon.style.transform = 'rotate(90deg)';
        } else {
            participantsDiv.style.display = 'none';
            expandIcon.textContent = '▶';
            expandIcon.style.transform = 'rotate(0deg)';
        }
    }

    closeDetails() {
        document.getElementById('person-details').innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">👤</div>
                <p>Click on a person in the network to view details</p>
            </div>
        `;
        document.getElementById('close-details-btn').style.display = 'none';
        this.network.unselectAll();
        this.showFullNetwork();
    }

    changeView(viewType) {
        this.currentView = viewType;

        // Update active button
        document.querySelectorAll('.view-controls button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.getElementById(`view-${viewType}-btn`).classList.add('active');

        // Filter edges based on view
        const allEdges = this.network.body.data.edges;
        allEdges.forEach(edge => {
            const edgeData = allEdges.get(edge.id);
            let visible = true;

            if (viewType === 'families') {
                visible = edgeData.relType === 'biological_parent';
            } else if (viewType === 'marriages') {
                visible = edgeData.relType === 'marriage';
            } else if (viewType === 'godparents') {
                visible = edgeData.relType === 'godparent';
            } else if (viewType === 'witnesses') {
                visible = edgeData.relType === 'witness';
            }

            allEdges.update({ id: edge.id, hidden: !visible });
        });

        this.network.stabilize();
    }

    applyFilters() {
        const surnameFilter = document.getElementById('filter-surname').checked;
        const selectedSurname = document.getElementById('surname-select').value;
        const yearFrom = parseInt(document.getElementById('year-from').value) || 1826;
        const yearTo = parseInt(document.getElementById('year-to').value) || 1914;

        const allNodes = this.network.body.data.nodes;
        allNodes.forEach(node => {
            const person = this.persons[node.id];
            let visible = true;

            // Surname filter
            if (surnameFilter && selectedSurname) {
                visible = visible && person.last_name === selectedSurname;
            }

            // Year filter
            const birthYear = this.extractYear(person.birth_date);
            if (birthYear) {
                visible = visible &&
                    birthYear >= yearFrom &&
                    birthYear <= yearTo;
            }

            allNodes.update({ id: node.id, hidden: !visible });
        });

        this.network.stabilize();
    }

    resetView() {
        // Clear search
        document.getElementById('search-input').value = '';
        document.getElementById('search-results').innerHTML = '';

        // Reset filters
        document.getElementById('filter-surname').checked = false;
        document.getElementById('surname-select').disabled = true;
        document.getElementById('year-from').value = '';
        document.getElementById('year-to').value = '';

        // Show all nodes and edges
        const allNodes = this.network.body.data.nodes;
        allNodes.forEach(node => {
            allNodes.update({ id: node.id, hidden: false });
        });

        const allEdges = this.network.body.data.edges;
        allEdges.forEach(edge => {
            allEdges.update({ id: edge.id, hidden: false });
        });

        // Reset view to all
        this.currentView = 'all';
        document.querySelectorAll('.view-controls button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.getElementById('view-all-btn').classList.add('active');

        // Fit network
        this.network.fit({
            animation: {
                duration: 1000,
                easingFunction: 'easeInOutQuad'
            }
        });
    }

    focusOnPerson(personId) {
        // Highlight person and their immediate connections
        const connectedNodes = this.network.getConnectedNodes(personId);
        const connectedEdges = this.network.getConnectedEdges(personId);

        // Dim all nodes
        const allNodes = this.network.body.data.nodes;
        allNodes.forEach(node => {
            const opacity = node.id === personId || connectedNodes.includes(node.id) ? 1 : 0.2;
            allNodes.update({ id: node.id, opacity: opacity });
        });

        // Dim all edges
        const allEdges = this.network.body.data.edges;
        allEdges.forEach(edge => {
            const opacity = connectedEdges.includes(edge.id) ? 1 : 0.1;
            allEdges.update({ id: edge.id, opacity: opacity });
        });

        this.network.focus(personId, {
            scale: 2,
            animation: {
                duration: 1000,
                easingFunction: 'easeInOutQuad'
            }
        });
    }

    focusOnPersonNetwork(personId) {
        // Show only the person's network including secondary connections
        // (e.g., selected person's children AND those children's godparents)

        const visibleNodes = new Set([personId]);
        const visibleEdges = new Set();

        // Get all direct connections
        const directlyConnected = this.network.getConnectedNodes(personId);
        directlyConnected.forEach(nodeId => visibleNodes.add(nodeId));

        // Get edges connecting to the selected person
        const allEdges = this.network.body.data.edges;
        allEdges.forEach(edge => {
            const edgeData = allEdges.get(edge.id);
            if (edgeData.from === personId || edgeData.to === personId) {
                visibleEdges.add(edge.id);
            }
        });

        // Add secondary connections: connections of directly connected people
        directlyConnected.forEach(connectedId => {
            const secondaryConnected = this.network.getConnectedNodes(connectedId);
            secondaryConnected.forEach(nodeId => visibleNodes.add(nodeId));

            // Add edges between primary and secondary connections
            allEdges.forEach(edge => {
                const edgeData = allEdges.get(edge.id);
                if ((edgeData.from === connectedId || edgeData.to === connectedId) &&
                    (visibleNodes.has(edgeData.from) && visibleNodes.has(edgeData.to))) {
                    visibleEdges.add(edge.id);
                }
            });
        });

        // Hide/show nodes
        const allNodes = this.network.body.data.nodes;
        allNodes.forEach(node => {
            allNodes.update({
                id: node.id,
                hidden: !visibleNodes.has(node.id)
            });
        });

        // Hide/show edges
        allEdges.forEach(edge => {
            allEdges.update({
                id: edge.id,
                hidden: !visibleEdges.has(edge.id)
            });
        });

        // Focus on the selected person
        this.network.focus(personId, {
            scale: 1.5,
            animation: {
                duration: 1000,
                easingFunction: 'easeInOutQuad'
            }
        });

        this.network.stabilize();
    }

    showFullNetwork() {
        // Show all nodes and edges
        const allNodes = this.network.body.data.nodes;
        const allEdges = this.network.body.data.edges;

        allNodes.forEach(node => {
            allNodes.update({ id: node.id, hidden: false });
        });

        allEdges.forEach(edge => {
            allEdges.update({ id: edge.id, hidden: false });
        });

        // Apply current view filter (all/families/marriages/etc.)
        this.changeView(this.currentView);

        // Fit to show everything
        this.network.fit({
            animation: {
                duration: 1000,
                easingFunction: 'easeInOutQuad'
            }
        });
    }

    updateStats() {
        // Stats bar was removed in Step 11, but keep this function for backward compatibility
        // Just check if elements exist before updating
        const totalPersonsEl = document.getElementById('total-persons');
        const totalEventsEl = document.getElementById('total-events');
        const totalRelationshipsEl = document.getElementById('total-relationships');
        const totalFamiliesEl = document.getElementById('total-families');

        if (totalPersonsEl) {
            totalPersonsEl.textContent = Object.keys(this.persons).length;
        }

        if (totalEventsEl) {
            totalEventsEl.textContent = Object.keys(this.events).length;
        }

        if (totalRelationshipsEl) {
            // Count relationships from events (birth = parent-child, marriage = spouse)
            let relationshipCount = 0;
            Object.values(this.events).forEach(event => {
                if (event.type === 'birth') {
                    const participants = Object.values(this.event_participations)
                        .filter(ep => ep.event_id === event.id);
                    const child = participants.find(p => p.role === 'child');
                    const parents = participants.filter(p => p.role === 'father' || p.role === 'mother');
                    if (child) relationshipCount += parents.length;
                } else if (event.type === 'marriage') {
                    const participants = Object.values(this.event_participations)
                        .filter(ep => ep.event_id === event.id);
                    const spouses = participants.filter(p => p.role === 'groom' || p.role === 'bride');
                    if (spouses.length === 2) relationshipCount += 1;
                }
            });
            totalRelationshipsEl.textContent = relationshipCount;
        }

        if (totalFamiliesEl) {
            // Count unique families (surnames)
            const surnames = new Set(Object.values(this.persons).map(p => p.last_name));
            totalFamiliesEl.textContent = surnames.size;
        }
    }

    hideLoading() {
        document.getElementById('loading-overlay').classList.add('hidden');
    }

    openEnrichmentReview() {
        if (typeof enrichmentReviewer !== 'undefined' && enrichmentReviewer) {
            enrichmentReviewer.open();
        }
    }

    closeEnrichmentReview() {
        if (typeof enrichmentReviewer !== 'undefined' && enrichmentReviewer) {
            enrichmentReviewer.close();
        }
    }

    handleInitialPersonSelection() {
        // Check if there's a person ID in the URL
        const urlParams = new URLSearchParams(window.location.search);
        let personId = urlParams.get('person');

        // If no person in URL, default to P0264
        if (!personId) {
            personId = 'P0264';
        }

        // Check if the person exists
        if (this.persons[personId]) {
            // Small delay to ensure network is fully initialized
            setTimeout(() => {
                this.showPersonDetails(personId);
                this.network.selectNodes([personId]);
                this.network.focus(personId, { scale: 1.5, animation: true });
            }, 500);
        } else {
            console.warn(`Person ${personId} not found in data`);
        }
    }

    expandSearchFilters() {
        const filtersSection = document.getElementById('search-filters-section');
        if (filtersSection) {
            filtersSection.style.display = 'block';
        }
    }

    collapseSearchFilters() {
        const filtersSection = document.getElementById('search-filters-section');
        if (filtersSection) {
            filtersSection.style.display = 'none';
        }
        // Clear search input
        document.getElementById('search-input').value = '';
        // Clear search results
        document.getElementById('search-results').innerHTML = '';
    }

    hasEventValidationIssue(eventId, personId) {
        // Step 23: Check for various data validation issues
        // Performance: Use cache
        const cacheKey = `${eventId}:${personId}`;
        if (this.validationCache.has(cacheKey)) {
            return this.validationCache.get(cacheKey);
        }

        const person = this.persons[personId];
        if (!person) {
            this.validationCache.set(cacheKey, false);
            return false;
        }

        const birthYear = this.extractYear(person.birth_date);
        const deathYear = this.extractYear(person.death_date);
        const event = this.events[eventId];
        const eventYear = event?.date?.year;

        // Performance: Use index instead of filtering all participations
        const personParticipations = this.participationsByPerson[personId] || [];

        // Check for multiple birth events
        const birthEvents = personParticipations.filter(ep => {
            const e = this.events[ep.event_id];
            return e && (e.type === 'birth' || e.type === 'baptism') && ep.role === 'child';
        });
        if (birthEvents.length > 1 && birthEvents.some(ep => ep.event_id === eventId)) {
            this.validationCache.set(cacheKey, true);
            return true;
        }

        // Check for multiple death events
        const deathEvents = personParticipations.filter(ep => {
            const e = this.events[ep.event_id];
            return e && (e.type === 'death' || e.type === 'burial') && ep.role === 'deceased';
        });
        if (deathEvents.length > 1 && deathEvents.some(ep => ep.event_id === eventId)) {
            this.validationCache.set(cacheKey, true);
            return true;
        }

        // Check for person participating in same event with multiple roles
        const rolesInThisEvent = personParticipations.filter(ep => ep.event_id === eventId);
        if (rolesInThisEvent.length > 1) {
            this.validationCache.set(cacheKey, true);
            return true;
        }

        if (!eventYear || !birthYear) {
            this.validationCache.set(cacheKey, false);
            return false;
        }

        const ageAtEvent = eventYear - birthYear;

        // Check age-based issues
        const participation = personParticipations.find(ep => ep.event_id === eventId);
        if (!participation) {
            this.validationCache.set(cacheKey, false);
            return false;
        }

        const role = participation.role;

        // Too young for certain roles (< 14 years)
        if (['groom', 'bride', 'witness', 'godparent', 'father', 'mother'].includes(role)) {
            if (ageAtEvent < 14) {
                this.validationCache.set(cacheKey, true);
                return true;
            }
        }

        // Female mother too old (> 50 years)
        if (role === 'mother' && person.gender === 'F' && ageAtEvent > 50) {
            this.validationCache.set(cacheKey, true);
            return true;
        }

        // Too old to participate (> 100 years)
        if (ageAtEvent > 100) {
            this.validationCache.set(cacheKey, true);
            return true;
        }

        this.validationCache.set(cacheKey, false);
        return false;
    }

    getRelationship(fromPersonId, toPersonId) {
        // Step 22: Calculate simple relationship between two people
        if (fromPersonId === toPersonId) return 'self';

        // Performance: Use cache
        const cacheKey = `${fromPersonId}:${toPersonId}`;
        if (this.relationshipCache.has(cacheKey)) {
            return this.relationshipCache.get(cacheKey);
        }

        const family = this.getFamily(fromPersonId);
        let result = null;

        // Check parents
        if (family.parents.some(p => p.id === toPersonId)) {
            const parent = family.parents.find(p => p.id === toPersonId);
            result = parent.role; // 'father' or 'mother'
            this.relationshipCache.set(cacheKey, result);
            return result;
        }

        // Check children
        if (family.children.includes(toPersonId)) {
            const child = this.persons[toPersonId];
            if (child.gender === 'M') result = 'son';
            else if (child.gender === 'F') result = 'daughter';
            else result = 'child';
            this.relationshipCache.set(cacheKey, result);
            return result;
        }

        // Check spouses
        if (family.spouses.includes(toPersonId)) {
            const spouse = this.persons[toPersonId];
            if (spouse.gender === 'M') result = 'husband';
            else if (spouse.gender === 'F') result = 'wife';
            else result = 'spouse';
            this.relationshipCache.set(cacheKey, result);
            return result;
        }

        // Check siblings
        if (family.siblings.includes(toPersonId)) {
            const sibling = this.persons[toPersonId];
            if (sibling.gender === 'M') result = 'brother';
            else if (sibling.gender === 'F') result = 'sister';
            else result = 'sibling';
            this.relationshipCache.set(cacheKey, result);
            return result;
        }

        // Check grandparents (parents of parents)
        for (const parent of family.parents) {
            const parentFamily = this.getFamily(parent.id);
            if (parentFamily.parents.some(p => p.id === toPersonId)) {
                const grandparent = this.persons[toPersonId];
                if (grandparent.gender === 'M') result = 'grandfather';
                else if (grandparent.gender === 'F') result = 'grandmother';
                else result = 'grandparent';
                this.relationshipCache.set(cacheKey, result);
                return result;
            }
        }

        // Check grandchildren (children of children)
        for (const childId of family.children) {
            const childFamily = this.getFamily(childId);
            if (childFamily.children.includes(toPersonId)) {
                const grandchild = this.persons[toPersonId];
                if (grandchild.gender === 'M') result = 'grandson';
                else if (grandchild.gender === 'F') result = 'granddaughter';
                else result = 'grandchild';
                this.relationshipCache.set(cacheKey, result);
                return result;
            }
        }

        // Check aunts/uncles (siblings of parents)
        for (const parent of family.parents) {
            const parentFamily = this.getFamily(parent.id);
            if (parentFamily.siblings.includes(toPersonId)) {
                const auntUncle = this.persons[toPersonId];
                if (auntUncle.gender === 'M') result = 'uncle';
                else if (auntUncle.gender === 'F') result = 'aunt';
                else result = 'aunt/uncle';
                this.relationshipCache.set(cacheKey, result);
                return result;
            }
        }

        // Check nieces/nephews (children of siblings)
        for (const siblingId of family.siblings) {
            const siblingFamily = this.getFamily(siblingId);
            if (siblingFamily.children.includes(toPersonId)) {
                const nieceNephew = this.persons[toPersonId];
                if (nieceNephew.gender === 'M') result = 'nephew';
                else if (nieceNephew.gender === 'F') result = 'niece';
                else result = 'niece/nephew';
                this.relationshipCache.set(cacheKey, result);
                return result;
            }
        }

        // Check cousins (children of aunts/uncles)
        for (const parent of family.parents) {
            const parentFamily = this.getFamily(parent.id);
            for (const auntUncleId of parentFamily.siblings) {
                const auntUncleFamily = this.getFamily(auntUncleId);
                if (auntUncleFamily.children.includes(toPersonId)) {
                    result = 'cousin';
                    this.relationshipCache.set(cacheKey, result);
                    return result;
                }
            }
        }

        // No direct relationship found
        this.relationshipCache.set(cacheKey, null);
        return null;
    }

    async deletePerson(personId) {
        try {
            const person = this.persons[personId];
            if (!person) {
                console.error('Person not found:', personId);
                return;
            }

            // Call API to delete person
            const response = await fetch('/api/delete-person', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ person_id: personId })
            });

            const result = await response.json();

            if (result.success) {
                // Remove person from local data
                delete this.persons[personId];

                // Remove from network
                this.nodes.remove(personId);

                // Remove event participations
                Object.keys(this.event_participations).forEach(epId => {
                    if (this.event_participations[epId].person_id === personId) {
                        delete this.event_participations[epId];
                    }
                });

                // Remove family relationships
                Object.keys(this.family_relationships).forEach(relId => {
                    const rel = this.family_relationships[relId];
                    if (rel.person_1_id === personId || rel.person_2_id === personId) {
                        delete this.family_relationships[relId];
                        this.edges.remove(relId);
                    }
                });

                // Remove deleted events
                if (result.deleted_events) {
                    result.deleted_events.forEach(eventId => {
                        delete this.events[eventId];
                    });
                }

                // Clear selected person
                this.selectedPerson = null;

                // Deselect in network
                this.network.unselectAll();

                // Clear URL parameter
                const url = new URL(window.location);
                url.searchParams.delete('person');
                window.history.pushState({}, '', url);

                // Show welcome message
                document.getElementById('details-panel').innerHTML = '<p>Select a person to view details</p>';

                console.log(`✓ Deleted person ${personId}`);
                if (result.deleted_events && result.deleted_events.length > 0) {
                    console.log(`  Deleted ${result.deleted_events.length} empty events`);
                }
            } else {
                console.error('Error deleting person:', result.error);
                alert('Error deleting person: ' + result.error);
            }
        } catch (error) {
            console.error('Error deleting person:', error);
            alert('Error deleting person: ' + error.message);
        }
    }

    async deleteEvent(eventId) {
        try {
            const event = this.events[eventId];
            if (!event) {
                console.error('Event not found:', eventId);
                return;
            }

            // Call API to delete event
            const response = await fetch('/api/delete-event', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ event_id: eventId })
            });

            const result = await response.json();

            if (result.success) {
                // Remove event from local data
                delete this.events[eventId];

                // Remove event participations
                Object.keys(this.event_participations).forEach(epId => {
                    if (this.event_participations[epId].event_id === eventId) {
                        delete this.event_participations[epId];
                    }
                });

                // Refresh the person details view if it's currently open
                if (this.selectedPerson) {
                    this.showPersonDetails(this.selectedPerson);
                }

                console.log(`✓ Deleted event ${eventId}`);
            } else {
                console.error('Error deleting event:', result.error);
                alert('Error deleting event: ' + result.error);
            }
        } catch (error) {
            console.error('Error deleting event:', error);
            alert('Error deleting event: ' + error.message);
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new GenealogyApp();
    window.genealogyApp = window.app; // Keep backward compatibility
});
