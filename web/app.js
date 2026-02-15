// Genealogical Database Application
class GenealogyApp {
    constructor() {
        this.persons = {};
        this.events = {};
        this.relationships = {};
        this.network = null;
        this.currentView = 'all';
        this.selectedPerson = null;
        this.init();
    }

    async init() {
        await this.loadData();
        this.setupUI();
        this.setupEventListeners();
        this.createNetwork();
        this.updateStats();
        this.hideLoading();
    }

    async loadData() {
        try {
            const response = await fetch('../data/genealogy_complete.json');
            const data = await response.json();

            this.persons = data.persons;
            this.events = data.events;
            this.relationships = data.relationships;

            console.log('Data loaded:', {
                persons: Object.keys(this.persons).length,
                events: Object.keys(this.events).length,
                relationships: Object.keys(this.relationships).length
            });
        } catch (error) {
            console.error('Error loading data:', error);
            alert('Error loading genealogical data. Please ensure the data files are in the correct location.');
        }
    }

    setupUI() {
        // Populate surname filter
        const surnames = new Set();
        Object.values(this.persons).forEach(person => {
            if (person.surname && person.surname !== 'Unknown') {
                surnames.add(person.surname);
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
    }

    createNetwork() {
        const container = document.getElementById('network-container');

        // Prepare nodes (persons)
        const nodes = [];
        Object.entries(this.persons).forEach(([id, person]) => {
            const birthYear = person.birth_year_estimate || '';
            const deathYear = person.death_year_estimate || '';
            const yearsLabel = birthYear || deathYear ? `\n(${birthYear || '?'}-${deathYear || '?'})` : '';

            nodes.push({
                id: id,
                label: `${person.given_name} ${person.surname}${yearsLabel}`,
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

        // Prepare edges (relationships)
        const edges = [];
        Object.entries(this.relationships).forEach(([id, rel]) => {
            const edgeConfig = {
                from: rel.from_person,
                to: rel.to_person,
                arrows: this.getEdgeArrows(rel.type),
                color: this.getEdgeColor(rel.type),
                width: 2,
                smooth: {
                    type: 'curvedCW',
                    roundness: 0.2
                },
                relType: rel.type,
                title: this.getRelationshipLabel(rel)
            };

            edges.push(edgeConfig);
        });

        // Add witness relationships from events
        const witnessConnections = new Set(); // Avoid duplicates
        Object.entries(this.events).forEach(([eventId, event]) => {
            if (event.witnesses && Array.isArray(event.witnesses)) {
                // Connect witnesses to the main person(s) in the event
                const mainPersons = [
                    event.child,
                    event.deceased,
                    event.groom,
                    event.bride
                ].filter(Boolean);

                event.witnesses.forEach(witnessId => {
                    mainPersons.forEach(mainPersonId => {
                        if (witnessId !== mainPersonId) {
                            // Create unique key to avoid duplicates
                            const key = `${witnessId}-${mainPersonId}`;
                            if (!witnessConnections.has(key)) {
                                witnessConnections.add(key);
                                edges.push({
                                    from: witnessId,
                                    to: mainPersonId,
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
            }
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
        const birth = person.birth_year_estimate ? `b. ${person.birth_year_estimate}` : '';
        const death = person.death_year_estimate ? `d. ${person.death_year_estimate}` : '';
        const years = [birth, death].filter(Boolean).join(', ');

        let tooltip = `<b>${person.given_name} ${person.surname}</b><br>`;
        tooltip += `ID: ${id}<br>`;
        if (years) tooltip += `${years}<br>`;
        if (person.maiden_name) tooltip += `Maiden: ${person.maiden_name}<br>`;
        if (person.occupations && person.occupations.length > 0) {
            tooltip += `Occupation: ${person.occupations.join(', ')}`;
        }

        return tooltip;
    }

    handleSearch() {
        const query = document.getElementById('search-input').value.trim().toLowerCase();
        if (!query) return;

        const results = [];
        Object.entries(this.persons).forEach(([id, person]) => {
            const fullName = `${person.given_name} ${person.surname}`.toLowerCase();
            const idMatch = id.toLowerCase().includes(query);
            const nameMatch = fullName.includes(query);
            const surnameMatch = person.surname.toLowerCase().includes(query);

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

            const birth = person.birth_year_estimate || '?';
            const death = person.death_year_estimate || '?';
            const gender = person.gender === 'M' ? '♂' : person.gender === 'F' ? '♀' : '?';

            item.innerHTML = `
                <div class="result-name">${person.given_name} ${person.surname} ${gender}</div>
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

    showPersonDetails(personId) {
        console.log('showPersonDetails called with:', personId);
        this.selectedPerson = personId;
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
                    ${person.given_name} ${person.surname}
                </div>
                <div class="person-id">${personId}</div>
                ${person.maiden_name ? `<div style="margin-top: 8px; color: #666;">née ${person.maiden_name}</div>` : ''}
                <div class="person-dates">
                    ${person.birth_year_estimate ? `Born: ~${person.birth_year_estimate}` : ''}
                    ${person.death_year_estimate ? `• Died: ~${person.death_year_estimate}` : ''}
                </div>
                <div style="margin-top: 10px;">
                    ${this.getGenderBadge(person.gender)}
                    ${person.occupations && person.occupations.length > 0 ?
                        person.occupations.map(occ => `<span class="badge">${occ}</span>`).join('') : ''}
                </div>
                <div class="person-actions">
                    <button class="btn-primary" onclick="editor.openEditModal('${personId}')">✏️ Edit</button>
                    <button class="btn-success" onclick="editor.selectPersonForMerge('${personId}')">🔗 Select for Merge</button>
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
                        ${parent.given_name} ${parent.surname} (${p.role})
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
                        ${spouse.given_name} ${spouse.surname}
                    </a></div>`;
                });
                html += '</div>';
            }

            if (family.children.length > 0) {
                html += '<div class="detail-item">';
                html += `<div class="detail-label">Children (${family.children.length})</div>`;
                family.children.forEach(childId => {
                    const child = this.persons[childId];
                    const birthYear = child.birth_year_estimate || '?';
                    html += `<div><a href="#" class="person-link" data-person-id="${childId}">
                        ${child.given_name} ${child.surname} (b. ${birthYear})
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
                        ${sibling.given_name} ${sibling.surname}
                    </a></div>`;
                });
                html += '</div>';
            }

            html += '</div>';
        }

        // Events section
        const events = this.getPersonEvents(personId);
        if (events.length > 0) {
            html += '<div class="detail-section"><div class="section-title">📅 Events</div>';
            events.slice(0, 10).forEach(event => {
                const year = event.year || (event.date && event.date.year) || '?';
                html += `
                    <div class="event-item">
                        <div class="event-year">${year}</div>
                        <span class="event-type">${event.type}</span>
                        <div class="event-text">${event.original_text || 'No text available'}</div>
                    </div>
                `;
            });
            if (events.length > 10) {
                html += `<p style="text-align: center; color: #666; margin-top: 10px;">
                    ... and ${events.length - 10} more events
                </p>`;
            }
            html += '</div>';
        }

        detailsContainer.innerHTML = html;

        // Add click handlers for person links
        detailsContainer.querySelectorAll('.person-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = e.target.getAttribute('data-person-id');
                this.showPersonDetails(targetId);
                this.network.selectNodes([targetId]);
                this.network.focus(targetId, { scale: 1.5, animation: true });
            });
        });
    }

    getGenderBadge(gender) {
        if (gender === 'M') return '<span class="badge male">♂ Male</span>';
        if (gender === 'F') return '<span class="badge female">♀ Female</span>';
        return '<span class="badge">? Unknown</span>';
    }

    getFamily(personId) {
        const family = {
            parents: [],
            children: [],
            spouses: [],
            siblings: []
        };

        Object.values(this.relationships).forEach(rel => {
            if (rel.type === 'biological_parent') {
                if (rel.to_person === personId) {
                    family.parents.push({ id: rel.from_person, role: rel.role });
                }
                if (rel.from_person === personId) {
                    family.children.push(rel.to_person);
                }
            } else if (rel.type === 'marriage') {
                if (rel.from_person === personId) {
                    family.spouses.push(rel.to_person);
                } else if (rel.to_person === personId) {
                    family.spouses.push(rel.from_person);
                }
            }
        });

        // Find siblings (same parents)
        const parentIds = family.parents.map(p => p.id);
        if (parentIds.length > 0) {
            Object.values(this.relationships).forEach(rel => {
                if (rel.type === 'biological_parent' &&
                    parentIds.includes(rel.from_person) &&
                    rel.to_person !== personId) {
                    if (!family.siblings.includes(rel.to_person)) {
                        family.siblings.push(rel.to_person);
                    }
                }
            });
        }

        return family;
    }

    getPersonEvents(personId) {
        const events = [];
        Object.values(this.events).forEach(event => {
            if (event.child === personId ||
                event.father === personId ||
                event.mother === personId ||
                event.deceased === personId ||
                event.groom === personId ||
                event.bride === personId ||
                (event.witnesses && event.witnesses.includes(personId)) ||
                (event.godparents && event.godparents.includes(personId))) {
                events.push(event);
            }
        });

        // Sort by year (handle both old and new data formats)
        events.sort((a, b) => {
            const yearA = a.year || (a.date && a.date.year) || 0;
            const yearB = b.year || (b.date && b.date.year) || 0;
            return yearA - yearB;
        });
        return events;
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
                visible = visible && person.surname === selectedSurname;
            }

            // Year filter
            if (person.birth_year_estimate) {
                visible = visible &&
                    person.birth_year_estimate >= yearFrom &&
                    person.birth_year_estimate <= yearTo;
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
        document.getElementById('total-persons').textContent = Object.keys(this.persons).length;
        document.getElementById('total-events').textContent = Object.keys(this.events).length;
        document.getElementById('total-relationships').textContent = Object.keys(this.relationships).length;

        // Count unique families (surnames)
        const surnames = new Set(Object.values(this.persons).map(p => p.surname));
        document.getElementById('total-families').textContent = surnames.size;
    }

    hideLoading() {
        document.getElementById('loading-overlay').classList.add('hidden');
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.genealogyApp = new GenealogyApp();
});
