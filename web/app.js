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
        this.currentModel = 'internal'; // 'internal' or 'gedcom'

        // Step 36/38: Geneteka import queue state
        this.genetikaImportQueue = [];
        this.genetikaImportIndex = 0;
        this.genetikaImportPersonId = null;
        this.genetikaImportType = null; // 'children', 'birth', 'marriage', 'death'

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

    // Step 50: Compact lifespan label, e.g. "1820–1875" or "?–1875"
    lifespan(person) {
        const b = this.extractYear(person?.birth_date) ?? '?';
        const d = this.extractYear(person?.death_date) ?? '?';
        return `${b}–${d}`;
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
        this.updateModelCounts();
        this.updateEditorButtons();
        this.hideLoading();

        // Handle URL-based person selection or default to P0264
        this.handleInitialPersonSelection();
    }

    async loadData() {
        try {
            // Load selected model with cache-busting to ensure fresh data
            const modelFile = this.currentModel === 'gedcom'
                ? 'gedcom_model.json'
                : 'genealogy_new_model.json';

            const response = await fetch(`../data/${modelFile}?t=${Date.now()}`);
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

    async switchModel(modelType) {
        if (this.currentModel === modelType) return;

        // Show loading indicator
        document.getElementById('network-container').innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; font-size: 1.2rem; color: #666;">Loading model...</div>';

        // Update model type
        this.currentModel = modelType;

        // Update tab UI
        document.getElementById('model-tab-internal').classList.toggle('active', modelType === 'internal');
        document.getElementById('model-tab-gedcom').classList.toggle('active', modelType === 'gedcom');

        // Clear selected person
        this.selectedPerson = null;
        document.getElementById('person-details').innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">👤</div>
                <p>Click on a person in the network to view details</p>
            </div>`;

        // Reload data
        await this.loadData();

        // Rebuild UI
        this.setupUI();
        this.createNetwork();
        this.updateModelCounts();

        // Disable/enable editor buttons based on model
        this.updateEditorButtons();

        console.log(`Switched to ${modelType} model`);
    }

    updateModelCounts() {
        const internalCount = document.getElementById('internal-count');
        const gedcomCount = document.getElementById('gedcom-count');

        if (this.currentModel === 'internal') {
            internalCount.textContent = `(${Object.keys(this.persons).length} persons)`;
            gedcomCount.textContent = '';
        } else {
            gedcomCount.textContent = `(${Object.keys(this.persons).length} persons)`;
            internalCount.textContent = '';
        }
    }

    updateEditorButtons() {
        // Disable editor buttons when viewing GEDCOM model (read-only)
        const isReadOnly = this.currentModel === 'gedcom';
        const editorButtons = document.querySelectorAll('.toolbar button');

        editorButtons.forEach(button => {
            if (button.id !== 'reset-btn' && button.id !== 'search-btn') {
                button.disabled = isReadOnly;
                button.style.opacity = isReadOnly ? '0.5' : '1';
                button.style.cursor = isReadOnly ? 'not-allowed' : 'pointer';
                if (isReadOnly) {
                    button.title = 'Editing disabled in GEDCOM view';
                } else {
                    button.title = '';
                }
            }
        });
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

        // Network options
        const options = {
            nodes: {
                shape: 'dot',
                size: 16,
                font: { size: 12 }
            },
            edges: {
                smooth: { enabled: true, type: 'dynamic' }
            },
            physics: {
                enabled: true,
                stabilization: { iterations: 200 },
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

        // Step 55: Start with empty network — only load related persons when one is selected
        const data = { nodes: new vis.DataSet([]), edges: new vis.DataSet([]) };
        this.network = new vis.Network(container, data, options);

        // Handle click events
        this.network.on('click', (params) => {
            if (params.nodes.length > 0) {
                const personId = params.nodes[0];
                try {
                    this.showPersonDetails(personId);
                } catch (error) {
                    console.error('Error showing person details:', error);
                    alert(`Error displaying person ${personId}: ${error.message}`);
                }
            }
            // Clicking empty space does nothing (Step 55: no full-network fallback)
        });

        // Handle double click to zoom in on person
        this.network.on('doubleClick', (params) => {
            if (params.nodes.length > 0) {
                const personId = params.nodes[0];
                this.network.focus(personId, {
                    scale: 2,
                    animation: { duration: 800, easingFunction: 'easeInOutQuad' }
                });
            }
        });

        // Step 55: View filter buttons are disabled — network is always person-scoped
        this.setViewControlsEnabled(false);
    }

    // Step 55: Compute set of person IDs reachable within `hops` from personId via shared events
    getRelatedPersonIds(personId, hops = 2) {
        const visited = new Set([personId]);
        let frontier = [personId];

        for (let h = 0; h < hops; h++) {
            const nextFrontier = [];
            frontier.forEach(id => {
                const eps = this.participationsByPerson[id] || [];
                eps.forEach(ep => {
                    const coParticipants = this.participationsByEvent[ep.event_id] || [];
                    coParticipants.forEach(coEp => {
                        if (!visited.has(coEp.person_id) && this.persons[coEp.person_id]) {
                            visited.add(coEp.person_id);
                            nextFrontier.push(coEp.person_id);
                        }
                    });
                });
            });
            frontier = nextFrontier;
            if (frontier.length === 0) break;
        }

        return visited;
    }

    // Step 55: Build and load a 2-hop subgraph for personId into the vis.js network
    buildPersonSubgraph(personId) {
        const visibleIds = this.getRelatedPersonIds(personId, 2);

        // Build nodes
        const nodes = [];
        visibleIds.forEach(id => {
            const person = this.persons[id];
            if (!person) return;
            const birthYear = this.extractYear(person.birth_date);
            const deathYear = this.extractYear(person.death_date);
            const yearsLabel = birthYear || deathYear ? `\n(${birthYear || '?'}-${deathYear || '?'})` : '';
            nodes.push({
                id,
                label: `${this.getFullName(person)}${yearsLabel}`,
                title: this.getPersonTooltip(id, person),
                color: this.getPersonColor(person.gender),
                font: { size: 14, color: '#333' },
                borderWidth: 2,
                borderWidthSelected: 4
            });
        });

        // Build edges
        const edges = [];
        const edgeSet = new Set();

        Object.values(this.events).forEach(event => {
            const participants = this.participationsByEvent[event.id] || [];

            if (event.type === 'birth') {
                const child = participants.find(p => p.role === 'child');
                const parents = participants.filter(p => p.role === 'father' || p.role === 'mother');
                if (child && visibleIds.has(child.person_id)) {
                    parents.forEach(parent => {
                        if (!visibleIds.has(parent.person_id)) return;
                        const key = `parent-${parent.person_id}-${child.person_id}`;
                        if (!edgeSet.has(key)) {
                            edgeSet.add(key);
                            edges.push({
                                from: parent.person_id, to: child.person_id,
                                arrows: this.getEdgeArrows('biological_parent'),
                                color: this.getEdgeColor('biological_parent'),
                                width: 2, smooth: { type: 'curvedCW', roundness: 0.2 },
                                relType: 'biological_parent', title: 'Parent of'
                            });
                        }
                    });
                }
            } else if (event.type === 'marriage') {
                const spouses = participants.filter(p => p.role === 'groom' || p.role === 'bride');
                if (spouses.length === 2 && visibleIds.has(spouses[0].person_id) && visibleIds.has(spouses[1].person_id)) {
                    const key = `spouse-${spouses[0].person_id}-${spouses[1].person_id}`;
                    const revKey = `spouse-${spouses[1].person_id}-${spouses[0].person_id}`;
                    if (!edgeSet.has(key) && !edgeSet.has(revKey)) {
                        edgeSet.add(key);
                        edges.push({
                            from: spouses[0].person_id, to: spouses[1].person_id,
                            arrows: this.getEdgeArrows('marriage'),
                            color: this.getEdgeColor('marriage'),
                            width: 2, smooth: { type: 'curvedCW', roundness: 0.2 },
                            relType: 'marriage', title: 'Married to'
                        });
                    }
                }
            }
        });

        // Witness edges
        const witnessSet = new Set();
        Object.entries(this.events).forEach(([eventId]) => {
            const participants = this.participationsByEvent[eventId] || [];
            const witnesses = participants.filter(ep => ep.role === 'witness' && visibleIds.has(ep.person_id));
            const mainParts = participants.filter(ep =>
                ['child', 'deceased', 'groom', 'bride'].includes(ep.role) && visibleIds.has(ep.person_id)
            );
            witnesses.forEach(w => {
                mainParts.forEach(m => {
                    if (w.person_id !== m.person_id) {
                        const key = `${w.person_id}-${m.person_id}`;
                        if (!witnessSet.has(key)) {
                            witnessSet.add(key);
                            edges.push({
                                from: w.person_id, to: m.person_id,
                                arrows: '', color: { color: '#95a5a6', opacity: 0.5 },
                                width: 1, dashes: [5, 5],
                                smooth: { type: 'curvedCW', roundness: 0.3 },
                                relType: 'witness', title: 'Witnessed event together'
                            });
                        }
                    }
                });
            });
        });

        // Replace network data
        const allNodes = this.network.body.data.nodes;
        const allEdges = this.network.body.data.edges;
        allNodes.clear();
        allEdges.clear();
        allNodes.add(nodes);
        allEdges.add(edges);

        // Select and focus on person
        this.network.selectNodes([personId]);
        setTimeout(() => {
            this.network.focus(personId, {
                scale: 1.5,
                animation: { duration: 800, easingFunction: 'easeInOutQuad' }
            });
        }, 300);
    }

    // Step 55: Enable/disable view filter buttons
    setViewControlsEnabled(enabled) {
        document.querySelectorAll('.view-controls button').forEach(btn => {
            btn.disabled = !enabled;
            btn.style.opacity = enabled ? '' : '0.4';
            btn.style.cursor = enabled ? '' : 'not-allowed';
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

            // Get parent information
            const family = this.getFamily(id);
            let parentInfo = '';
            if (family.parents.length > 0) {
                const parentNames = family.parents.map(p => {
                    const parent = this.persons[p.id];
                    return `${parent.first_name} ${parent.last_name} (${p.role})`;
                }).join(', ');
                parentInfo = ` • Parents: ${parentNames}`;
            }

            item.innerHTML = `
                <div class="result-name">${this.getFullName(person)} ${gender}</div>
                <div class="result-info">
                    ${id} • ${birth}-${death}
                    ${person.maiden_name ? `• maiden: ${person.maiden_name}` : ''}
                    ${parentInfo}
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
                    ${person.tags && person.tags.length > 0 ? person.tags.map(t => `<span class="badge tag-badge">${t}</span>`).join('') : ''}
                </div>
                <div class="person-actions">
                    <button class="btn-primary" onclick="editor.openEditModal('${personId}')">✏️ Edit</button>
                    <button class="btn-success" onclick="editor.selectPersonForMerge('${personId}')">🔗 Merge</button>
                    <button class="btn-danger" onclick="genealogyApp.deletePerson('${personId}')">🗑️ Delete</button>
                    <button class="btn-secondary" onclick="app.openGeneteka('${personId}')">🔍 Geneteka</button>
                    <button class="btn-secondary" onclick="app.openGenetikaImportOptions('${personId}')">📥 Import</button>
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
                    html += `
                        <div style="display: flex; justify-content: space-between; align-items: center; margin: 4px 0;">
                            <a href="#" class="person-link" data-person-id="${p.id}">
                                ${this.getFullNameWithMaiden(parent)} (${p.role}, ${this.lifespan(parent)})
                            </a>
                            <button class="btn-secondary"
                                    style="padding: 2px 8px; font-size: 0.7rem; margin-left: 8px;"
                                    onclick="event.stopPropagation(); eventEditor.openEditEventModal('${p.eventId}')">
                                📝 Event
                            </button>
                        </div>`;
                });
                html += '</div>';
            }

            if (family.spouses.length > 0) {
                html += '<div class="detail-item">';
                html += '<div class="detail-label">Spouse(s)</div>';
                const sortedSpouses = [...family.spouses].sort((a, b) => {
                    const ya = this.events[a.eventId]?.date?.year ?? null;
                    const yb = this.events[b.eventId]?.date?.year ?? null;
                    if (ya === null && yb === null) return 0;
                    if (ya === null) return -1;
                    if (yb === null) return 1;
                    return ya - yb;
                });
                sortedSpouses.forEach(s => {
                    const spouse = this.persons[s.id];
                    html += `
                        <div style="display: flex; justify-content: space-between; align-items: center; margin: 4px 0;">
                            <a href="#" class="person-link" data-person-id="${s.id}">
                                ${this.getFullNameWithMaiden(spouse)} (${this.lifespan(spouse)})
                            </a>
                            <button class="btn-secondary"
                                    style="padding: 2px 8px; font-size: 0.7rem; margin-left: 8px;"
                                    onclick="event.stopPropagation(); eventEditor.openEditEventModal('${s.eventId}')">
                                📝 Event
                            </button>
                        </div>`;
                });
                html += '</div>';
            }

            if (family.children.length > 0) {
                html += '<div class="detail-item">';
                html += `<div class="detail-label">Children (${family.children.length})</div>`;
                const sortedChildren = [...family.children].sort((a, b) => {
                    const ya = this.extractYear(this.persons[a.id]?.birth_date) || Infinity;
                    const yb = this.extractYear(this.persons[b.id]?.birth_date) || Infinity;
                    return ya - yb;
                });
                sortedChildren.forEach(c => {
                    const child = this.persons[c.id];
                    html += `
                        <div style="display: flex; justify-content: space-between; align-items: center; margin: 4px 0;">
                            <a href="#" class="person-link" data-person-id="${c.id}">
                                ${this.getFullNameWithMaiden(child)} (${this.lifespan(child)})
                            </a>
                            <button class="btn-secondary"
                                    style="padding: 2px 8px; font-size: 0.7rem; margin-left: 8px;"
                                    onclick="event.stopPropagation(); eventEditor.openEditEventModal('${c.eventId}')">
                                📝 Event
                            </button>
                        </div>`;
                });
                html += '</div>';
            }

            if (family.siblings.length > 0) {
                html += '<div class="detail-item">';
                html += `<div class="detail-label">Siblings (${family.siblings.length})</div>`;
                const sortedSiblings = [...family.siblings].sort((a, b) => {
                    const ya = this.extractYear(this.persons[a]?.birth_date) || Infinity;
                    const yb = this.extractYear(this.persons[b]?.birth_date) || Infinity;
                    return ya - yb;
                });
                sortedSiblings.forEach(siblingId => {
                    const sibling = this.persons[siblingId];
                    html += `<div><a href="#" class="person-link" data-person-id="${siblingId}">
                        ${this.getFullNameWithMaiden(sibling)} (${this.lifespan(sibling)})
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

        // Step 56: Notes section (before events)
        if (person.notes) {
            html += `<div class="detail-section">
                <div class="section-title">📝 Notes</div>
                <div style="white-space: pre-wrap; color: #555; font-size: 0.9rem; line-height: 1.5;">${person.notes}</div>
            </div>`;
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
                } else if (event.isFamilyEvent) {
                    // Step 34: Show relationship between primary participant(s) and the blood witness
                    const primaryParticipants = this.getEventPrimaryParticipants(eventId);
                    const relParts = [];
                    primaryParticipants.forEach(({ personId: primId }) => {
                        if (primId && this.selectedPerson && primId !== this.selectedPerson) {
                            const rel = this.getRelationship(this.selectedPerson, primId);
                            const primPerson = this.persons[primId];
                            if (rel && primPerson) {
                                relParts.push(`${this.getFullName(primPerson)} (your <strong>${rel}</strong>)`);
                            } else if (primPerson) {
                                relParts.push(this.getFullName(primPerson));
                            }
                        }
                    });
                    const relText = relParts.length > 0 ? ' - ' + relParts.join(' &amp; ') : '';
                    personRoleHTML = `<div style="margin-top: 8px; padding: 6px 8px; background: #e3f2fd; border-left: 3px solid #1976d2; border-radius: 3px; font-size: 0.9rem;">
                        <strong>👨‍👩‍👧‍👦 Family Event</strong>${relText}
                    </div>`;
                }

                // Step 23: Check for validation issues
                const validationWarning = this.hasEventValidationIssue(eventId, personId) ? ' <span style="color: red; font-weight: bold;" title="Data issue detected">!</span>' : '';

                // Step 32: Add "assumed" indicator for family events
                const familyEventIndicator = event.isFamilyEvent ? ' <span style="color: #667eea; font-size: 0.8rem; font-style: italic;">(assumed)</span>' : '';

                html += `
                    <div class="event-item expandable-event" data-event-id="${eventId}">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div class="event-header" onclick="app.toggleEventDetails('${eventId}')" style="flex: 1;">
                                <div style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
                                    <span class="event-expand-icon" id="expand-icon-${eventId}">▶</span>
                                    <div class="event-year">${year}${validationWarning}</div>
                                    <span class="event-type">${event.type === 'generic' ? (event.title || 'generic') : event.type}${familyEventIndicator}</span>
                                    <span style="font-size: 0.75rem; color: #999; font-family: monospace;">${eventId}</span>
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
                            ${this.getEventParticipantsHTML(eventId, event.isFamilyEvent)}
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        }

        detailsContainer.innerHTML = html;

        // Step 55: Build and display the person's 2-hop network subgraph
        this.buildPersonSubgraph(personId);

        // Add click handlers for person links (family and participants)
        detailsContainer.querySelectorAll('.person-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('data-person-id');
                if (targetId) {
                    this.showPersonDetails(targetId);
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
                                role: 'father',
                                eventId: ep.event_id
                            });
                        }
                    });
                    mothers.forEach(m => {
                        if (!family.parents.find(p => p.id === m.person_id)) {
                            family.parents.push({
                                id: m.person_id,
                                role: 'mother',
                                eventId: ep.event_id
                            });
                        }
                    });
                } else if (ep.person_id === personId && (ep.role === 'father' || ep.role === 'mother')) {
                    // This person is a parent - collect children
                    if (child && !family.children.find(c => c.id === child.person_id)) {
                        family.children.push({
                            id: child.person_id,
                            eventId: ep.event_id
                        });
                    }
                }
            }

            // Marriage events contain spouse relationships
            // Only consider if person is bride/groom, not witness or other role
            if (event.type === 'marriage' && ep.person_id === personId && (ep.role === 'groom' || ep.role === 'bride')) {
                // Performance: Use participationsByEvent index
                const participants = (this.participationsByEvent[ep.event_id] || [])
                    .filter(e => e.role === 'groom' || e.role === 'bride');

                participants.forEach(p => {
                    if (p.person_id !== personId && !family.spouses.find(s => s.id === p.person_id)) {
                        family.spouses.push({
                            id: p.person_id,
                            eventId: ep.event_id
                        });
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
        const familyEventIds = new Set(); // Track which events are family events (Step 32)

        // Find all events where this person participated directly
        Object.values(this.event_participations).forEach(ep => {
            if (ep.person_id === personId) {
                eventIds.add(ep.event_id);
            }
        });

        // Step 32: Find family events (blood relatives up to 2 steps)
        const bloodRelatives = this.getBloodRelativesUpTo2Steps(personId);

        // Step 42: Only qualify family events where blood relative has a primary role
        const primaryRoles = new Set(['child', 'father', 'mother', 'deceased', 'groom', 'bride', 'participant']);
        const familyEventTypes = new Set(['birth', 'baptism', 'marriage', 'death', 'burial', 'generic']);

        // For each blood relative, find their birth/baptism/marriage/death/burial events (primary roles only)
        bloodRelatives.forEach(relativeId => {
            Object.values(this.event_participations).forEach(ep => {
                if (ep.person_id === relativeId && primaryRoles.has(ep.role)) {
                    const event = this.events[ep.event_id];
                    if (event && familyEventTypes.has(event.type)) {
                        // Don't add if person is already a direct participant
                        if (!eventIds.has(ep.event_id)) {
                            eventIds.add(ep.event_id);
                            familyEventIds.add(ep.event_id); // Mark as family event
                        }
                    }
                }
            });
        });

        // Step 49: Also include events from spouses of person and spouses of blood relatives
        const spouseIds = new Set();
        // Person's own spouses
        const ownFamily = this.getFamily(personId);
        ownFamily.spouses.forEach(s => spouseIds.add(s.id));
        // Spouses of blood relatives
        bloodRelatives.forEach(relId => {
            const relFamily = this.getFamily(relId);
            relFamily.spouses.forEach(s => {
                if (s.id !== personId) spouseIds.add(s.id);
            });
        });
        // Add events from spouses using same rules (primaryRoles + familyEventTypes)
        spouseIds.forEach(spouseId => {
            (this.participationsByPerson[spouseId] || []).forEach(ep => {
                if (primaryRoles.has(ep.role)) {
                    const event = this.events[ep.event_id];
                    if (event && familyEventTypes.has(event.type)) {
                        if (!eventIds.has(ep.event_id)) {
                            eventIds.add(ep.event_id);
                            familyEventIds.add(ep.event_id);
                        }
                    }
                }
            });
        });

        // Step 33: Filter family events by person's lifetime
        const person = this.persons[personId];
        const birthYear = person?.birth_date?.year ?? null;
        const deathYear = person?.death_date?.year ?? null;

        let upperBound;
        if (deathYear !== null) {
            upperBound = deathYear;
        } else {
            // Compute last explicit event year (direct participation only)
            let lastExplicitYear = null;
            eventIds.forEach(id => {
                if (!familyEventIds.has(id)) {
                    const yr = this.events[id]?.date?.year;
                    if (yr != null && (lastExplicitYear === null || yr > lastExplicitYear)) {
                        lastExplicitYear = yr;
                    }
                }
            });
            if (lastExplicitYear !== null) {
                upperBound = lastExplicitYear + 20;
            } else if (birthYear !== null) {
                upperBound = birthYear + 100;
            } else {
                upperBound = null;
            }
        }

        familyEventIds.forEach(id => {
            const eventYear = this.events[id]?.date?.year ?? null;
            if (eventYear === null) { eventIds.delete(id); return; } // Step 37: hide family events with no date
            if (birthYear !== null && eventYear < birthYear) { eventIds.delete(id); return; }
            if (upperBound !== null && eventYear > upperBound) { eventIds.delete(id); }
        });

        // Collect the actual event objects
        eventIds.forEach(eventId => {
            const event = this.events[eventId];
            if (event) {
                // Mark event as family event if it's in familyEventIds
                const eventCopy = { ...event };
                if (familyEventIds.has(eventId)) {
                    eventCopy.isFamilyEvent = true;
                }
                events.push(eventCopy);
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

    getBloodRelativesUpTo2Steps(personId) {
        // Step 32: Get all blood relatives up to 2 steps (both ascendants and descendants)
        const relatives = new Set();
        const family = this.getFamily(personId);

        // 1 step: Parents
        family.parents.forEach(p => relatives.add(p.id));

        // 1 step: Children
        family.children.forEach(c => relatives.add(c.id));

        // 2 steps: Siblings (through parents)
        family.siblings.forEach(s => relatives.add(s));

        // 2 steps: Grandparents (parents of parents)
        family.parents.forEach(parent => {
            const parentFamily = this.getFamily(parent.id);
            parentFamily.parents.forEach(gp => relatives.add(gp.id));
        });

        // 2 steps: Grandchildren (children of children)
        family.children.forEach(child => {
            const childFamily = this.getFamily(child.id);
            childFamily.children.forEach(gc => relatives.add(gc.id));
        });

        return relatives;
    }

    getEventGodparents(eventId) {
        // Get all godparents for this event
        const godparents = Object.values(this.event_participations)
            .filter(ep => ep.event_id === eventId && ep.role === 'godparent')
            .map(ep => ep.person_id);
        return godparents;
    }

    getEventParticipantsHTML(eventId, isFamilyEvent = false) {
        // Performance: Use index instead of filtering all participations
        const participants = this.participationsByEvent[eventId] || [];

        if (participants.length === 0) {
            return '<div style="color: #666; font-style: italic;">No participants recorded</div>';
        }

        // Get event date for age calculation
        const event = this.events[eventId];
        const eventYear = event?.date?.year;

        // Step 32: Add family witness indication at the top if this is a family event
        let familyWitnessHeader = '';
        if (isFamilyEvent && this.selectedPerson) {
            familyWitnessHeader = '<div style="background: #e3f2fd; padding: 8px; border-radius: 4px; margin-bottom: 10px; font-size: 0.9rem; color: #1976d2;"><strong>👨‍👩‍👧‍👦 Family Event</strong> - You are viewing this as an implicit family witness (blood relative within 2 steps)</div>';
        }

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

        let html = familyWitnessHeader + '<div style="font-weight: 600; margin-bottom: 8px;">Participants:</div>';

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
        this.selectedPerson = null;
        // Step 55: Clear network when no person is selected
        this.network.body.data.nodes.clear();
        this.network.body.data.edges.clear();
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
        if (family.children.some(c => c.id === toPersonId)) {
            const child = this.persons[toPersonId];
            if (child.gender === 'M') result = 'son';
            else if (child.gender === 'F') result = 'daughter';
            else result = 'child';
            this.relationshipCache.set(cacheKey, result);
            return result;
        }

        // Check spouses
        if (family.spouses.some(s => s.id === toPersonId)) {
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
        for (const child of family.children) {
            const childFamily = this.getFamily(child.id);
            if (childFamily.children.some(c => c.id === toPersonId)) {
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
                if (auntUncleFamily.children.some(c => c.id === toPersonId)) {
                    result = 'cousin';
                    this.relationshipCache.set(cacheKey, result);
                    return result;
                }
            }
        }

        // Step 49: Check in-laws - spouses of children (son/daughter-in-law)
        for (const child of family.children) {
            const childFamily = this.getFamily(child.id);
            if (childFamily.spouses.some(s => s.id === toPersonId)) {
                const inLaw = this.persons[toPersonId];
                if (inLaw.gender === 'M') result = 'son-in-law';
                else if (inLaw.gender === 'F') result = 'daughter-in-law';
                else result = 'child-in-law';
                this.relationshipCache.set(cacheKey, result);
                return result;
            }
        }

        // Step 49: Check in-laws - spouses of siblings (brother/sister-in-law)
        for (const siblingId of family.siblings) {
            const siblingFamily = this.getFamily(siblingId);
            if (siblingFamily.spouses.some(s => s.id === toPersonId)) {
                const inLaw = this.persons[toPersonId];
                if (inLaw.gender === 'M') result = 'brother-in-law';
                else if (inLaw.gender === 'F') result = 'sister-in-law';
                else result = 'sibling-in-law';
                this.relationshipCache.set(cacheKey, result);
                return result;
            }
        }

        // Step 49: Check in-laws - spouses of parents (step-parent)
        for (const parent of family.parents) {
            const parentFamily = this.getFamily(parent.id);
            if (parentFamily.spouses.some(s => s.id === toPersonId)) {
                const stepParent = this.persons[toPersonId];
                if (stepParent.gender === 'M') result = 'step-father';
                else if (stepParent.gender === 'F') result = 'step-mother';
                else result = 'step-parent';
                this.relationshipCache.set(cacheKey, result);
                return result;
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

    getEventPrimaryParticipants(eventId) {
        // Step 34: Return primary participants based on event type
        const participants = this.participationsByEvent[eventId] || [];
        const event = this.events[eventId];
        if (!event) return [];

        if (event.type === 'birth') {
            const child = participants.find(ep => ep.role === 'child');
            return child ? [{ personId: child.person_id, role: 'child' }] : [];
        } else if (event.type === 'death') {
            const deceased = participants.find(ep => ep.role === 'deceased');
            return deceased ? [{ personId: deceased.person_id, role: 'deceased' }] : [];
        } else if (event.type === 'marriage') {
            const results = [];
            const groom = participants.find(ep => ep.role === 'groom');
            const bride = participants.find(ep => ep.role === 'bride');
            if (groom) results.push({ personId: groom.person_id, role: 'groom' });
            if (bride) results.push({ personId: bride.person_id, role: 'bride' });
            return results;
        } else if (event.type === 'generic') {
            return participants
                .filter(ep => ep.role === 'participant')
                .map(ep => ({ personId: ep.person_id, role: 'participant' }));
        }
        // Fallback to first participant
        if (participants.length > 0) {
            return [{ personId: participants[0].person_id, role: participants[0].role }];
        }
        return [];
    }

    openGeneteka(personId) {
        // Step 35: Open Geneteka search in new tab
        const person = this.persons[personId];
        if (!person) return;
        const lastName = encodeURIComponent(person.last_name || '');
        const firstName = encodeURIComponent(person.first_name || '');
        const url = `https://geneteka.genealodzy.pl/index.php?op=gt&lang=pol&bdm=B&w=13sk&rid=3382&search_lastname=${lastName}&search_name=${firstName}&search_lastname2=&search_name2=&from_date=&to_date=`;
        window.open(url, '_blank');
    }

    // Step 38: Open type-selection modal
    openGenetikaImportOptions(personId) {
        this.genetikaImportPersonId = personId;
        document.getElementById('geneteka-import-options-modal').style.display = 'block';
    }

    _closeGenetikaOptionsModal() {
        document.getElementById('geneteka-import-options-modal').style.display = 'none';
    }

    // ── shared helper: fetch records and queue them ──────────────────────────
    async _fetchAndQueueGenetikaRecords(lastName, firstName, type, filterFn, emptyMsg) {
        const ln = encodeURIComponent(lastName);
        const fn = encodeURIComponent(firstName);
        try {
            const response = await fetch(`/api/geneteka-import?first_name=${fn}&last_name=${ln}&type=${type}`);
            const data = await response.json();
            if (!data.success) {
                alert(`Geneteka lookup failed: ${data.error || 'Unknown error'}`);
                return null;
            }
            const all = data.records || [];
            const filtered = filterFn ? all.filter(filterFn) : all;
            if (filtered.length === 0) {
                alert(emptyMsg || `No matching records found on Geneteka.`);
                return null;
            }
            return filtered;
        } catch (e) {
            console.error('Geneteka lookup error:', e);
            alert('Failed to fetch data from Geneteka. Check the server console for details.');
            return null;
        }
    }

    // ── 1. Children Import (Step 36 — unchanged logic) ───────────────────────
    async startGenetikaChildrenImport() {
        this._closeGenetikaOptionsModal();
        const personId = this.genetikaImportPersonId;
        const person = this.persons[personId];
        if (!person) return;

        const fn = (person.first_name || '').toLowerCase();
        const gender = person.gender;

        const firstName = person.first_name || '';
        let filterFn = null;
        if (gender === 'M') filterFn = r => this._namesMatch(r.imie_ojca, firstName);
        else if (gender === 'F') filterFn = r => this._namesMatch(r.imie_matki, firstName);

        let records = await this._fetchAndQueueGenetikaRecords(
            person.last_name || '', person.first_name || '', 'birth', filterFn,
            `No birth records found where ${person.first_name} appears as a parent.`
        );
        if (!records) {
            // fall back to unfiltered
            records = await this._fetchAndQueueGenetikaRecords(
                person.last_name || '', person.first_name || '', 'birth', null,
                'No birth records found on Geneteka for this person.'
            );
        }
        if (!records) return;

        this.genetikaImportQueue = records;
        this.genetikaImportIndex = 0;
        this.genetikaImportType = 'children';
        this.openNextGenetikaRecord();
    }

    // ── 2. Birth Lookup — person is the child ───────────────────────────────
    async startGenetikaBirthLookup() {
        this._closeGenetikaOptionsModal();
        const personId = this.genetikaImportPersonId;
        const person = this.persons[personId];
        if (!person) return;

        const firstName = person.first_name || '';
        const fnLower = firstName.toLowerCase();

        // For females use maiden name; fall back to last name
        const isFemale = person.gender === 'F';
        const primaryLastName = (isFemale && person.maiden_name) ? person.maiden_name : (person.last_name || '');

        const makeFilter = (lastName) => r =>
            this._namesMatch(r.imie_dziecka, firstName) &&
            this._namesMatch(r.nazwisko, lastName);

        let records = await this._fetchAndQueueGenetikaRecords(
            primaryLastName, firstName, 'birth', makeFilter(primaryLastName), null
        );

        // If female with maiden name and no results, retry with last name
        if (!records && isFemale && person.maiden_name && person.last_name &&
                person.maiden_name !== person.last_name) {
            records = await this._fetchAndQueueGenetikaRecords(
                person.last_name, firstName, 'birth', makeFilter(person.last_name), null
            );
        }

        if (!records) {
            alert(`No birth records found for ${firstName} ${primaryLastName} on Geneteka.`);
            return;
        }

        this.genetikaImportQueue = records;
        this.genetikaImportIndex = 0;
        this.genetikaImportType = 'birth';
        this.openNextGenetikaRecord();
    }

    // ── 3. Marriage Lookup ────────────────────────────────────────────────────
    async startGenetikaMarriageLookup() {
        this._closeGenetikaOptionsModal();
        const personId = this.genetikaImportPersonId;
        const person = this.persons[personId];
        if (!person) return;

        const firstName = person.first_name || '';
        const fnLower = firstName.toLowerCase();
        const isFemale = person.gender === 'F';
        const primaryLastName = (isFemale && person.maiden_name) ? person.maiden_name : (person.last_name || '');

        // Match person as groom (M) or bride (F)
        const makeFilter = (lastName) => r => {
            if (isFemale) {
                return this._namesMatch(r.imie_pani, firstName) &&
                       this._namesMatch(r.nazwisko_pani, lastName);
            } else {
                return this._namesMatch(r.imie_pana, firstName) &&
                       this._namesMatch(r.nazwisko_pana, lastName);
            }
        };

        let records = await this._fetchAndQueueGenetikaRecords(
            primaryLastName, firstName, 'marriage', makeFilter(primaryLastName), null
        );

        // Female fallback: retry with last name
        if (!records && isFemale && person.maiden_name && person.last_name &&
                person.maiden_name !== person.last_name) {
            records = await this._fetchAndQueueGenetikaRecords(
                person.last_name, firstName, 'marriage', makeFilter(person.last_name), null
            );
        }

        if (!records) {
            alert(`No marriage records found for ${firstName} ${primaryLastName} on Geneteka.`);
            return;
        }

        this.genetikaImportQueue = records;
        this.genetikaImportIndex = 0;
        this.genetikaImportType = 'marriage';
        this.openNextGenetikaRecord();
    }

    // ── 4. Death Lookup ───────────────────────────────────────────────────────
    async startGenetikaDeathLookup() {
        this._closeGenetikaOptionsModal();
        const personId = this.genetikaImportPersonId;
        const person = this.persons[personId];
        if (!person) return;

        const firstName = person.first_name || '';
        const fnLower = firstName.toLowerCase();
        const isFemale = person.gender === 'F';
        const lastName = person.last_name || '';

        // Fetch raw results once per search term, then apply filters in sequence.
        const fetchAll = async (ln, fn) => {
            const encLn = encodeURIComponent(ln);
            const encFn = encodeURIComponent(fn);
            try {
                const resp = await fetch(`/api/geneteka-import?first_name=${encFn}&last_name=${encLn}&type=death`);
                const data = await resp.json();
                return data.success ? (data.records || []) : [];
            } catch (e) {
                console.error('Geneteka death fetch error:', e);
                return [];
            }
        };

        // Search 1: by last name
        let all = await fetchAll(lastName, firstName);

        // Filter 1a: fuzzy first name + surname
        let filtered = all.filter(r =>
            this._namesMatch(r.imie, firstName) &&
            this._namesMatch(r.nazwisko, lastName)
        );

        // Filter 1b: first name + "Inne nazwiska" tooltip contains surname
        if (!filtered.length) {
            filtered = all.filter(r =>
                this._namesMatch(r.imie, firstName) &&
                (r.uwagi || '').toLowerCase().includes(lastName.toLowerCase())
            );
        }

        // Filter 1c: first name + parent data (surname match)
        if (!filtered.length) {
            const parents = this._getPersonParents(personId);
            if (parents.fatherFirstName || parents.motherMaiden) {
                filtered = all.filter(r => {
                    const fnMatch = this._namesMatch(r.imie, firstName);
                    const fatherMatch = parents.fatherFirstName &&
                        this._namesMatch(r.imie_ojca, parents.fatherFirstName);
                    const motherMatch = parents.motherMaiden &&
                        this._namesMatch(r.nazwisko_matki, parents.motherMaiden);
                    return fnMatch && (fatherMatch || motherMatch);
                });
            }
        }

        // Search 2: by maiden name (female only) — same three-tier sequence
        if (!filtered.length && isFemale && person.maiden_name && person.maiden_name !== lastName) {
            const maidenName = person.maiden_name;
            all = await fetchAll(maidenName, firstName);

            filtered = all.filter(r =>
                this._namesMatch(r.imie, firstName) &&
                this._namesMatch(r.nazwisko, maidenName)
            );

            if (!filtered.length) {
                filtered = all.filter(r =>
                    this._namesMatch(r.imie, firstName) &&
                    (r.uwagi || '').toLowerCase().includes(maidenName.toLowerCase())
                );
            }

            if (!filtered.length) {
                const parents = this._getPersonParents(personId);
                if (parents.fatherFirstName || parents.motherMaiden) {
                    filtered = all.filter(r => {
                        const fnMatch = this._namesMatch(r.imie, firstName);
                        const fatherMatch = parents.fatherFirstName &&
                            this._namesMatch(r.imie_ojca, parents.fatherFirstName);
                        const motherMatch = parents.motherMaiden &&
                            this._namesMatch(r.nazwisko_matki, parents.motherMaiden);
                        return fnMatch && (fatherMatch || motherMatch);
                    });
                }
            }
        }

        // Final fallback: both parent first names only (no surname), year-bounded
        if (!filtered.length) {
            const parents = this._getPersonParents(personId);
            const birthYear = person.birth_date?.year ?? null;
            if (parents.fatherFirstName && parents.motherFirstName) {
                filtered = all.filter(r => {
                    if (birthYear !== null) {
                        const rok = parseInt(r.rok);
                        if (isNaN(rok) || rok < birthYear || rok > birthYear + 100) return false;
                    }
                    return this._namesMatch(r.imie, firstName) &&
                           this._namesMatch(r.imie_ojca, parents.fatherFirstName) &&
                           this._namesMatch(r.imie_matki, parents.motherFirstName);
                });
            }
        }

        if (!filtered.length) {
            alert(`No death records found for ${firstName} ${lastName} on Geneteka.`);
            return;
        }

        this.genetikaImportQueue = filtered;
        this.genetikaImportIndex = 0;
        this.genetikaImportType = 'death';
        this.openNextGenetikaRecord();
    }

    // ── Fuzzy name matching for historical Polish records ─────────────────────

    _normalizePolishName(name) {
        if (!name) return '';
        return name.toLowerCase()
            .replace(/ą/g, 'a').replace(/ę/g, 'e').replace(/ó/g, 'o')
            .replace(/ś/g, 's').replace(/ź/g, 'z').replace(/ż/g, 'z')
            .replace(/ć/g, 'c').replace(/ń/g, 'n').replace(/ł/g, 'l')
            .replace(/y/g, 'i'); // y ↔ i: Wiktorya/Wiktoria, Surdey/Surdej, etc.
    }

    _levenshtein(a, b) {
        if (Math.abs(a.length - b.length) > 3) return 99;
        let row = Array.from({length: b.length + 1}, (_, i) => i);
        for (let i = 1; i <= a.length; i++) {
            const next = [i];
            for (let j = 1; j <= b.length; j++) {
                next[j] = a[i-1] === b[j-1] ? row[j-1]
                    : 1 + Math.min(row[j], next[j-1], row[j-1]);
            }
            row = next;
        }
        return row[b.length];
    }

    // Returns true if recordName and searchName are considered the same name,
    // accounting for historical Polish spelling variants.
    _namesMatch(recordName, searchName) {
        if (!recordName || !searchName) return false;
        const a = this._normalizePolishName(recordName);
        const b = this._normalizePolishName(searchName);
        if (a === b) return true;
        // Substring: catches "Jarosz" inside "Jaroszek", short forms, etc.
        if (a.includes(b) || b.includes(a)) return true;
        // Levenshtein: threshold 1 for short names, 2 for longer ones
        const threshold = Math.max(a.length, b.length) <= 5 ? 1 : 2;
        return this._levenshtein(a, b) <= threshold;
    }

    // Returns parent names from model birth event
    _getPersonParents(personId) {
        let fatherFirstName = null;
        let motherFirstName = null;
        let motherMaiden = null;

        for (const ep of Object.values(this.event_participations)) {
            if (ep.person_id !== personId || ep.role !== 'child') continue;
            const eventId = ep.event_id;
            for (const ep2 of Object.values(this.event_participations)) {
                if (ep2.event_id !== eventId) continue;
                const parent = this.persons[ep2.person_id];
                if (!parent) continue;
                if (ep2.role === 'father') fatherFirstName = parent.first_name || null;
                if (ep2.role === 'mother') {
                    motherFirstName = parent.first_name || null;
                    motherMaiden = parent.maiden_name || null;
                }
            }
            break; // use first birth event found
        }

        return { fatherFirstName, motherFirstName, motherMaiden };
    }

    // ── Queue runner ──────────────────────────────────────────────────────────
    openNextGenetikaRecord() {
        if (this.genetikaImportIndex >= this.genetikaImportQueue.length) {
            if (eventEditor) eventEditor.onCloseCallback = null;
            const total = this.genetikaImportQueue.length;
            if (eventEditor) eventEditor.showNotification(`Geneteka import complete. Reviewed ${total} record(s).`, 'success');
            this.genetikaImportQueue = [];
            this.genetikaImportIndex = 0;
            this.genetikaImportPersonId = null;
            this.genetikaImportType = null;
            return;
        }

        const record = this.genetikaImportQueue[this.genetikaImportIndex];
        const current = this.genetikaImportIndex + 1;
        const total = this.genetikaImportQueue.length;
        this.genetikaImportIndex++;

        if (!eventEditor) return;
        eventEditor.onCloseCallback = () => this.openNextGenetikaRecord();

        if (this.genetikaImportType === 'marriage') {
            eventEditor.openMarriageFromGeneteka(record, this.genetikaImportPersonId, current, total);
        } else if (this.genetikaImportType === 'death') {
            eventEditor.openDeathFromGeneteka(record, this.genetikaImportPersonId, current, total);
        } else {
            // 'children' or 'birth' — both use birth event form
            eventEditor.openBirthFromGeneteka(record, this.genetikaImportPersonId, current, total);
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
