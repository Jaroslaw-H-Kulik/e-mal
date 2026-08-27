// Event Registry - Step 67: Global events list view

class EventRegistry {
    constructor(app) {
        this.app = app;
        this._filterYearFrom = null;
        this._filterYearTo = null;
        this._filterSettlement = '';
        this._setupPanel();
    }

    _setupPanel() {
        if (document.getElementById('events-list-panel')) return;
        const vizPanel = document.querySelector('.visualization-panel');
        if (!vizPanel) return;
        const div = document.createElement('div');
        div.id = 'events-list-panel';
        div.style.display = 'none';
        div.style.height = '100%';
        div.style.overflowY = 'auto';
        div.style.background = '#fff';
        div.style.boxSizing = 'border-box';
        vizPanel.appendChild(div);
    }

    _panel() { return document.getElementById('events-list-panel'); }

    isVisible() {
        const p = this._panel();
        return p && p.style.display !== 'none';
    }

    show() {
        if (window.documentManager && documentManager.currentDocId) {
            documentManager.closeDocumentImagePanel();
        }
        const networkEl = document.getElementById('network-container');
        const panel = this._panel();
        if (!networkEl || !panel) return;

        networkEl.style.display = 'none';
        panel.style.display = 'block';

        const vizPanel = panel.closest('.visualization-panel');
        const h2 = vizPanel?.querySelector('.panel-header h2');
        const controls = vizPanel?.querySelector('.view-controls');
        if (h2) h2.textContent = '📋 All Events';
        if (controls) controls.style.display = 'none';

        window.history.pushState({}, '', '/events');
        this.render();
    }

    _closePanel() {
        const networkEl = document.getElementById('network-container');
        const panel = this._panel();
        if (!networkEl || !panel) return;

        panel.style.display = 'none';
        networkEl.style.display = 'block';

        const vizPanel = panel.closest('.visualization-panel');
        const h2 = vizPanel?.querySelector('.panel-header h2');
        const controls = vizPanel?.querySelector('.view-controls');
        if (h2) h2.textContent = 'Community Network';
        if (controls) controls.style.display = '';
    }

    hide() {
        this._closePanel();
        const dest = this.app.selectedPerson ? '/person/' + this.app.selectedPerson : '/';
        window.history.pushState({}, '', dest);
    }

    _placeName(placeId) {
        if (!placeId) return null;
        return this.app.places[placeId]?.name || null;
    }

    _placeLabel(placeId) {
        if (!placeId) return null;
        const p = this.app.places[placeId];
        if (!p) return null;
        return p.house_number ? `${p.name} ${p.house_number}` : p.name;
    }

    _personName(personId) {
        const p = this.app.persons[personId];
        return p ? this.app.getFullName(p) : personId;
    }

    _participantLabel(event) {
        const eps = this.app.participationsByEvent[event.id] || [];
        switch (event.type) {
            case 'birth': {
                const c = eps.find(e => e.role === 'child');
                return c ? this._personName(c.person_id) : '';
            }
            case 'death': {
                const d = eps.find(e => e.role === 'deceased');
                return d ? this._personName(d.person_id) : '';
            }
            case 'marriage': {
                const parts = [];
                const gr = eps.find(e => e.role === 'groom');
                const br = eps.find(e => e.role === 'bride');
                if (gr) parts.push(this._personName(gr.person_id));
                if (br) parts.push(this._personName(br.person_id));
                return parts.join(' & ');
            }
            case 'generic':
                return eps.length > 0 ? this._personName(eps[0].person_id) : '';
            default:
                return '';
        }
    }

    _typeLabel(event) {
        switch (event.type) {
            case 'birth':    return 'Birth';
            case 'death':    return 'Death';
            case 'marriage': return 'Marriage';
            case 'generic':  return event.title || 'Generic';
            case 'global':   return event.title || 'Global';
            default:         return event.type;
        }
    }

    _typeColor(type) {
        switch (type) {
            case 'birth':    return '#4A90E2';
            case 'death':    return '#7f8c8d';
            case 'marriage': return '#E91E8C';
            case 'generic':  return '#FF9800';
            case 'global':   return '#27ae60';
            default:         return '#95a5a6';
        }
    }

    _allSettlements() {
        const names = new Set();
        Object.values(this.app.events).forEach(ev => {
            if (!ev.date?.year) return;
            const name = this._placeName(ev.place_id);
            if (name) names.add(name);
        });
        return Array.from(names).sort();
    }

    _participantsFlatHTML(eventId) {
        const eps = this.app.participationsByEvent[eventId] || [];
        if (eps.length === 0) return '<div style="color:#999;font-size:0.85rem;">No participants recorded</div>';
        return eps.map(ep => {
            const name = this._personName(ep.person_id);
            return `<div style="font-size:0.85rem;padding:2px 0;">
                <span style="color:#888;text-transform:capitalize;min-width:80px;display:inline-block;">${ep.role}:</span>
                <a href="javascript:void(0)"
                   onclick="app.showPersonDetails('${ep.person_id}')"
                   style="color:#667eea;text-decoration:none;">${name}</a>
                <span style="color:#bbb;font-size:0.75rem;margin-left:4px;">${ep.person_id}</span>
            </div>`;
        }).join('');
    }

    toggleExpand(eventId) {
        const div = document.getElementById(`reg-participants-${eventId}`);
        const icon = document.getElementById(`reg-expand-icon-${eventId}`);
        if (!div) return;
        const isOpen = div.style.display !== 'none';
        div.style.display = isOpen ? 'none' : 'block';
        if (icon) icon.textContent = isOpen ? '▶' : '▼';
    }

    openEventForEdit(eventId) {
        eventEditor.openEditEventModal(eventId);
        eventEditor.currentPersonId = null;
        eventEditor.onCloseCallback = () => this.render();
    }

    async _deleteEvent(eventId) {
        await this.app.deleteEvent(eventId);
        if (this.isVisible()) this.render();
    }

    render() {
        const panel = this._panel();
        if (!panel) return;

        let events = Object.values(this.app.events).filter(e => e.date?.year);

        if (this._filterYearFrom) events = events.filter(e => e.date.year >= this._filterYearFrom);
        if (this._filterYearTo)   events = events.filter(e => e.date.year <= this._filterYearTo);
        if (this._filterSettlement) {
            events = events.filter(e => this._placeName(e.place_id) === this._filterSettlement);
        }

        events.sort((a, b) => {
            const score = e => e.date.year * 10000 + (e.date.month || 0) * 100 + (e.date.day || 0);
            return score(a) - score(b);
        });

        const settlements = this._allSettlements();
        const settlementOpts = settlements.map(s =>
            `<option value="${s}"${s === this._filterSettlement ? ' selected' : ''}>${s}</option>`
        ).join('');

        let html = `
        <div style="padding:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                <h3 style="margin:0;font-size:1.1rem;">
                    📋 All Events
                    <span style="font-weight:normal;font-size:0.85rem;color:#888;">&nbsp;${events.length} shown</span>
                </h3>
                <button class="btn-secondary" style="padding:4px 10px;font-size:0.85rem;"
                        onclick="eventRegistry.hide()">✕ Close</button>
            </div>
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:14px;
                        padding:10px;background:#f8f9fa;border-radius:8px;font-size:0.85rem;">
                <span style="font-weight:600;color:#555;">Filter:</span>
                <input type="number" placeholder="Year from" min="1700" max="2100"
                       value="${this._filterYearFrom || ''}"
                       style="width:95px;padding:4px 7px;border:1px solid #ddd;border-radius:4px;"
                       onchange="eventRegistry._filterYearFrom=this.value?parseInt(this.value):null;eventRegistry.render()">
                <span style="color:#aaa;">–</span>
                <input type="number" placeholder="Year to" min="1700" max="2100"
                       value="${this._filterYearTo || ''}"
                       style="width:95px;padding:4px 7px;border:1px solid #ddd;border-radius:4px;"
                       onchange="eventRegistry._filterYearTo=this.value?parseInt(this.value):null;eventRegistry.render()">
                <select style="padding:4px 7px;border:1px solid #ddd;border-radius:4px;"
                        onchange="eventRegistry._filterSettlement=this.value;eventRegistry.render()">
                    <option value="">All settlements</option>
                    ${settlementOpts}
                </select>
                <button class="btn-secondary" style="padding:3px 9px;font-size:0.8rem;"
                        onclick="eventRegistry._filterYearFrom=null;eventRegistry._filterYearTo=null;eventRegistry._filterSettlement='';eventRegistry.render()">↺</button>
            </div>`;

        if (events.length === 0) {
            html += '<div style="text-align:center;color:#999;padding:40px;">No events match the current filters.</div>';
        } else {
            events.forEach(ev => {
                const typeLabel   = this._typeLabel(ev);
                const participant = this._participantLabel(ev);
                const dateStr     = this.app.formatFlexibleDate(ev.date);
                const placeLabel  = this._placeLabel(ev.place_id);
                const color       = this._typeColor(ev.type);
                const participants = this._participantsFlatHTML(ev.id);

                html += `
                <div class="event-item" style="margin-bottom:4px;padding:6px 10px;">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span id="reg-expand-icon-${ev.id}"
                              onclick="eventRegistry.toggleExpand('${ev.id}')"
                              style="cursor:pointer;color:#667eea;flex-shrink:0;font-size:0.75rem;user-select:none;">▶</span>
                        <span style="background:${color};color:#fff;padding:2px 7px;border-radius:10px;
                                     font-size:0.72rem;white-space:nowrap;flex-shrink:0;">${typeLabel}</span>
                        <span style="font-size:0.82rem;color:#888;white-space:nowrap;flex-shrink:0;
                                     min-width:60px;">${dateStr}</span>
                        <span style="font-size:0.88rem;font-weight:500;flex:1;min-width:0;
                                     overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${participant}</span>
                        ${placeLabel ? `<span style="font-size:0.75rem;color:#aaa;white-space:nowrap;flex-shrink:0;">📍 ${placeLabel}</span>` : ''}
                        <span style="font-size:0.72rem;color:#ccc;flex-shrink:0;">${ev.id}</span>
                        <button class="btn-secondary" style="padding:3px 8px;font-size:0.75rem;flex-shrink:0;"
                                onclick="eventRegistry.openEventForEdit('${ev.id}')">Edit</button>
                        <button class="btn-danger" style="padding:3px 8px;font-size:0.75rem;flex-shrink:0;"
                                onclick="eventRegistry._deleteEvent('${ev.id}')">Delete</button>
                    </div>
                    <div id="reg-participants-${ev.id}"
                         style="display:none;margin-top:8px;padding:8px 10px;background:#f8f9fa;border-radius:4px;">
                        ${participants}
                    </div>
                </div>`;
            });
        }

        html += '</div>';
        panel.innerHTML = html;
    }
}
