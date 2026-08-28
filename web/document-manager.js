// Document Manager - Steps 57, 58, 59

class DocumentManager {
    constructor(app) {
        this.app = app;
        this.documents = app.documents || {};
        this.currentDocId = null;
        this.currentPageIndex = 0;
        this.editingDocId = null;
        this.pendingFiles = []; // {dataUrl, ext, name} for new uploads
        this.zoomLevel = 1;
        this._panX = 0;
        this._panY = 0;
        this._naturalWidth = null;
        this._naturalHeight = null;
        this._wheelHandler = null;
        this._keyHandler = null;

        this._setupOptionsModal();
    }

    // ── Helpers ────────────────────────────────────────────────────────────────

    _panel() {
        return document.getElementById('person-details');
    }

    // ── Options modal ──────────────────────────────────────────────────────────

    _setupOptionsModal() {
        const html = `
        <div id="documents-options-modal" class="modal" style="display:none;">
            <div class="modal-content" style="max-width:400px;">
                <div class="modal-header">
                    <h2>📄 Documents</h2>
                    <button class="close-modal" onclick="documentManager.closeOptions()">&times;</button>
                </div>
                <div class="modal-body">
                    <p style="color:#666;margin-bottom:16px;">What would you like to do?</p>
                    <div style="display:grid;gap:12px;">
                        <button class="btn-success" style="padding:14px;font-size:1rem;text-align:left;"
                                onclick="documentManager.showAddForm()">
                            ➕ Add Document
                            <div style="font-size:0.82rem;color:#fff;opacity:0.8;margin-top:4px;">Upload a new document with pages</div>
                        </button>
                        <button class="btn-secondary" style="padding:14px;font-size:1rem;text-align:left;"
                                onclick="documentManager.showList()">
                            📋 Browse Documents
                            <div style="font-size:0.82rem;color:#888;margin-top:4px;">View all documents in the archive</div>
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
        document.body.insertAdjacentHTML('beforeend', html);
    }

    showOptions() {
        document.getElementById('documents-options-modal').style.display = 'block';
    }

    closeOptions() {
        document.getElementById('documents-options-modal').style.display = 'none';
    }

    // ── Document list view ─────────────────────────────────────────────────────

    showList() {
        this.closeOptions();
        this.closeDocumentImagePanel();
        const docs = Object.values(this.documents);
        docs.sort((a, b) => (a.name || '').localeCompare(b.name || ''));

        let html = `<div style="padding:15px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
                <h3 style="margin:0;">📄 Documents</h3>
                <button class="btn-success" style="padding:6px 12px;" onclick="documentManager.showAddForm()">+ Add</button>
            </div>`;

        if (docs.length === 0) {
            html += '<div style="color:#666;text-align:center;padding:30px;">No documents yet.</div>';
        } else {
            docs.forEach(doc => {
                const tagsHtml = (doc.tags || []).map(t =>
                    `<span style="background:#e8f4f8;padding:2px 6px;border-radius:10px;font-size:0.75rem;margin-right:3px;">#${t}</span>`
                ).join('');
                html += `
                <div class="event-item" style="cursor:pointer;margin-bottom:8px;" onclick="documentManager.showCard('${doc.id}')">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                            <div style="font-weight:600;">${doc.name || '(untitled)'}</div>
                            <div style="font-size:0.85rem;color:#666;margin-top:3px;">
                                ${doc.date ? doc.date : ''}
                                ${tagsHtml}
                            </div>
                        </div>
                        <div style="font-family:monospace;font-size:0.75rem;color:#999;white-space:nowrap;margin-left:8px;">${doc.id}</div>
                    </div>
                </div>`;
            });
        }

        html += '</div>';
        this._panel().innerHTML = html;
    }

    // ── Add document form ──────────────────────────────────────────────────────

    showAddForm() {
        this.closeOptions();
        this.closeDocumentImagePanel();
        this.pendingFiles = [];

        this._panel().innerHTML = `<div style="padding:15px;">
            <h3 style="margin-top:0;">📄 Add Document</h3>
            <div class="form-group">
                <label>Name *</label>
                <input type="text" id="doc-name" placeholder="e.g. Birth register 1842" style="width:100%;box-sizing:border-box;">
            </div>
            <div class="form-group">
                <label>Year</label>
                <input type="number" id="doc-year" placeholder="e.g. 1842" min="1600" max="2100" style="width:100%;box-sizing:border-box;">
            </div>
            <div class="form-group">
                <label>Notes</label>
                <textarea id="doc-notes" rows="3" placeholder="Additional notes..." style="width:100%;box-sizing:border-box;"></textarea>
            </div>
            <div class="form-group">
                <label>Tags (comma-separated)</label>
                <input type="text" id="doc-tags" placeholder="birth, scan, 1842" style="width:100%;box-sizing:border-box;">
            </div>
            <div class="form-group">
                <label>External Link</label>
                <input type="text" id="doc-link" placeholder="https://..." style="width:100%;box-sizing:border-box;">
            </div>
            <div class="form-group">
                <label>Pages (jpg, png, tiff)</label>
                <input type="file" id="doc-files" multiple accept=".jpg,.jpeg,.png,.tif,.tiff"
                       onchange="documentManager.handleFileSelect(event)"
                       style="width:100%;box-sizing:border-box;">
                <div id="doc-pages-preview" style="margin-top:10px;"></div>
            </div>
            <div style="display:flex;gap:10px;margin-top:20px;">
                <button class="btn-primary" onclick="documentManager.saveNewDocument()">Save Document</button>
                <button class="btn-secondary" onclick="documentManager.showList()">Cancel</button>
            </div>
        </div>`;
    }

    handleFileSelect(event) {
        const files = Array.from(event.target.files).sort((a, b) => a.name.localeCompare(b.name));
        this.pendingFiles = new Array(files.length);

        const promises = files.map((file, i) => new Promise(resolve => {
            const reader = new FileReader();
            reader.onload = e => {
                const rawExt = file.name.split('.').pop().toLowerCase();
                const ext = rawExt === 'jpeg' ? 'jpg' : rawExt === 'tif' ? 'tiff' : rawExt;
                this.pendingFiles[i] = { dataUrl: e.target.result, ext, name: file.name };
                resolve();
            };
            reader.readAsDataURL(file);
        }));

        Promise.all(promises).then(() => this._renderPagesPreview());
    }

    _renderPagesPreview() {
        const container = document.getElementById('doc-pages-preview');
        if (!container) return;

        if (this.pendingFiles.length === 0) { container.innerHTML = ''; return; }

        let html = '';
        this.pendingFiles.forEach((pf, i) => {
            html += `<div style="display:flex;align-items:center;gap:8px;padding:6px;background:#f8f9fa;border-radius:4px;margin-bottom:4px;">
                <img src="${pf.dataUrl}" style="width:40px;height:40px;object-fit:cover;border-radius:2px;flex-shrink:0;">
                <span style="flex:1;font-size:0.85rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${pf.name}</span>
                <button type="button" onclick="documentManager.movePendingPage(${i},-1)" ${i === 0 ? 'disabled' : ''} style="padding:2px 6px;">↑</button>
                <button type="button" onclick="documentManager.movePendingPage(${i},1)" ${i === this.pendingFiles.length - 1 ? 'disabled' : ''} style="padding:2px 6px;">↓</button>
                <button type="button" onclick="documentManager.removePendingPage(${i})" style="padding:2px 6px;color:#c00;">✕</button>
            </div>`;
        });
        container.innerHTML = html;
    }

    movePendingPage(index, direction) {
        const newIndex = index + direction;
        if (newIndex < 0 || newIndex >= this.pendingFiles.length) return;
        [this.pendingFiles[index], this.pendingFiles[newIndex]] = [this.pendingFiles[newIndex], this.pendingFiles[index]];
        this._renderPagesPreview();
    }

    removePendingPage(index) {
        this.pendingFiles.splice(index, 1);
        this._renderPagesPreview();
    }

    async saveNewDocument() {
        const name = document.getElementById('doc-name')?.value.trim();
        if (!name) { alert('Document name is required.'); return; }

        const yearVal = document.getElementById('doc-year')?.value;
        const notes  = document.getElementById('doc-notes')?.value.trim();
        const tagsRaw = document.getElementById('doc-tags')?.value || '';
        const link   = document.getElementById('doc-link')?.value.trim();
        const tags   = tagsRaw.split(',').map(t => t.trim()).filter(Boolean);

        const pages = this.pendingFiles.map(pf => ({
            data: pf.dataUrl.split(',')[1],
            ext: pf.ext,
        }));

        try {
            const res = await fetch('/api/add-document', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    date: yearVal ? parseInt(yearVal) : null,
                    notes, tags, link, events: [], pages,
                }),
            });
            const result = await res.json();
            if (result.success) {
                this.documents[result.document.id] = result.document;
                this.app.documents = this.documents;
                this.showCard(result.document.id);
            } else {
                alert('Error saving document: ' + (result.error || 'Unknown error'));
            }
        } catch (e) {
            alert('Error saving document: ' + e.message);
        }
    }

    // ── Document card ──────────────────────────────────────────────────────────

    showCard(docId, pushUrl = true) {
        this.currentDocId = docId;
        this.currentPageIndex = 0;
        this._renderCard();
        this._renderImagePanel();
        if (pushUrl) {
            window.history.pushState({}, '', '/document/' + docId);
        }
    }

    _renderCard() {
        const doc = this.documents[this.currentDocId];
        if (!doc) return;

        const tagsHtml = (doc.tags || []).map(t =>
            `<span style="background:#e8f4f8;padding:2px 6px;border-radius:10px;font-size:0.78rem;margin-right:3px;">#${t}</span>`
        ).join('') || '<span style="color:#aaa;">—</span>';

        // Page info + transcription (image is shown in center panel)
        let pageInfoHtml = '';
        if (doc.pages && doc.pages.length > 0) {
            const page = doc.pages[this.currentPageIndex];
            const isFirst = this.currentPageIndex === 0;
            const isLast  = this.currentPageIndex === doc.pages.length - 1;

            pageInfoHtml = `
            <div style="margin:12px 0;padding:10px;background:#f8f9fa;border-radius:6px;border:1px solid #e0e0e0;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                    <button onclick="documentManager.prevPage()" ${isFirst ? 'disabled' : ''} style="padding:4px 10px;">← Prev</button>
                    <span style="font-size:0.85rem;color:#555;font-weight:600;">Page ${this.currentPageIndex + 1} of ${doc.pages.length}</span>
                    <button onclick="documentManager.nextPage()" ${isLast ? 'disabled' : ''} style="padding:4px 10px;">Next →</button>
                </div>
                <div style="font-family:monospace;font-size:0.75rem;color:#888;text-align:center;">${page.filename}</div>
                ${page.transcription ? `<div style="margin-top:8px;padding:8px;background:#fffbf0;border-radius:4px;font-size:0.85rem;white-space:pre-wrap;border:1px solid #f0e8c0;">${page.transcription}</div>` : ''}
            </div>`;
        }

        // Build events section
        const eventsSection = this._renderDocumentEvents(doc);

        this._panel().innerHTML = `<div style="padding:15px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
                <div>
                    <h3 style="margin:0 0 4px 0;">📄 ${doc.name || '(untitled)'}</h3>
                    <div style="font-family:monospace;font-size:0.78rem;color:#999;">${doc.id}</div>
                </div>
                <div style="display:flex;gap:6px;">
                    <button class="btn-secondary" style="padding:4px 10px;" onclick="documentManager.showEditForm('${doc.id}')">✏️ Edit</button>
                    <button class="btn-danger" style="padding:4px 10px;" onclick="documentManager.deleteDocument('${doc.id}')">🗑️ Delete</button>
                </div>
            </div>

            ${pageInfoHtml}

            <div style="display:grid;gap:8px;font-size:0.9rem;margin-bottom:16px;">
                <div><strong>Year:</strong> ${doc.date || '—'}</div>
                <div><strong>Tags:</strong> ${tagsHtml}</div>
                ${doc.link ? `<div><strong>Link:</strong> <a href="${doc.link}" target="_blank" style="word-break:break-all;">${doc.link}</a></div>` : ''}
                ${doc.notes ? `<div><strong>Notes:</strong><br><span style="white-space:pre-wrap;color:#555;">${doc.notes}</span></div>` : ''}
            </div>

            ${eventsSection}
        </div>`;

        // Wire up participant person-link clicks
        this._panel().querySelectorAll('.participant-link').forEach(link => {
            link.addEventListener('click', e => {
                e.preventDefault();
                const personId = link.getAttribute('data-person-id');
                if (personId && window.app) app.showPersonDetails(personId);
            });
        });
    }

    _renderDocumentEvents(doc) {
        const app = window.app;
        const eventIds = (doc.events || [])
            .filter(eid => app && app.events && app.events[eid])
            .sort((a, b) => {
                const ya = app.events[a]?.date?.year || 0;
                const yb = app.events[b]?.date?.year || 0;
                return ya - yb;
            });

        const count = eventIds.length;
        let html = `<div class="detail-section">
            <div class="section-title">📅 Events (${count})</div>`;

        if (count === 0) {
            html += '<div style="color:#aaa;font-size:0.85rem;padding:8px 0;">No events linked. Use Edit to link events.</div>';
        } else {
            eventIds.forEach(eventId => {
                const event = app.events[eventId];
                const year = event.date?.year || '?';
                const eventContent = event.content || event.original_text || 'No content available';

                let typeLabel;
                if (event.type === 'generic') {
                    typeLabel = `📜 ${event.title || event.type}`;
                } else if (event.type === 'global') {
                    typeLabel = event.title || event.type;
                } else {
                    typeLabel = event.type;
                }

                const participantsHtml = app.getEventParticipantsHTML(eventId, false);

                html += `
                    <div class="event-item expandable-event" data-event-id="${eventId}">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                            <div class="event-header" onclick="app.toggleEventDetails('${eventId}')" style="flex:1;">
                                <div style="display:flex;align-items:center;gap:10px;cursor:pointer;">
                                    <span class="event-expand-icon" id="expand-icon-${eventId}">▶</span>
                                    <div class="event-year">${year}</div>
                                    <span class="event-type">${typeLabel}</span>
                                    ${(() => { const place = event.place_id && app.places[event.place_id]; if (!place) return ''; const hn = place.house_number ? ` ${place.house_number}` : ''; return `<span class="badge settlement-badge">📍 ${place.name}${hn}</span>`; })()}
                                    <span style="font-size:0.75rem;color:#999;font-family:monospace;">${eventId}</span>
                                </div>
                            </div>
                            <button class="btn-secondary" style="padding:4px 8px;font-size:0.75rem;margin-right:4px;"
                                    onclick="event.stopPropagation(); eventEditor.openEditEventModal('${eventId}')">Edit</button>
                            <button class="btn-danger" style="padding:4px 8px;font-size:0.75rem;"
                                    onclick="event.stopPropagation(); genealogyApp.deleteEvent('${eventId}')">Delete</button>
                        </div>
                        <div class="event-text" onclick="app.toggleEventDetails('${eventId}')" style="cursor:pointer;">
                            ${eventContent}
                        </div>
                        <div class="event-participants" id="participants-${eventId}"
                             style="display:none;margin-top:10px;padding:10px;background:#f8f9fa;border-radius:4px;">
                            ${participantsHtml}
                        </div>
                    </div>`;
            });
        }

        html += '</div>';
        return html;
    }

    _renderImagePanel() {
        const doc = this.documents[this.currentDocId];
        const networkEl  = document.getElementById('network-container');
        const imagePanel = document.getElementById('document-image-panel');
        if (!networkEl || !imagePanel) return;

        // Swap visibility
        networkEl.style.display = 'none';
        imagePanel.style.display = 'flex';
        imagePanel.style.flexDirection = 'column';
        imagePanel.style.alignItems = 'stretch';
        imagePanel.style.padding = '0';

        // Update panel header
        const panelHeader = imagePanel.closest('.visualization-panel')?.querySelector('.panel-header h2');
        const viewControls = imagePanel.closest('.visualization-panel')?.querySelector('.view-controls');
        if (panelHeader) panelHeader.textContent = `📄 ${doc?.name || ''}`;
        if (viewControls) viewControls.style.display = 'none';

        // Remove old event listeners
        this._removeZoomListeners();

        // Render image
        if (!doc || !doc.pages || doc.pages.length === 0) {
            imagePanel.innerHTML = '<div style="color:#aaa;padding:40px;text-align:center;">No pages</div>';
            return;
        }

        const page = doc.pages[this.currentPageIndex];
        const zoomPct = Math.round(this.zoomLevel * 100);

        imagePanel.innerHTML = `
            <div id="doc-zoom-toolbar" style="
                display:flex; align-items:center; gap:8px;
                padding:8px 14px; background:rgba(0,0,0,0.55);
                backdrop-filter:blur(4px); flex-shrink:0; z-index:10;
                border-bottom:1px solid rgba(255,255,255,0.1);">
                <button onclick="documentManager.zoomOut()" title="Zoom out (−)"
                        style="background:#444;color:#eee;border:none;border-radius:4px;padding:4px 10px;font-size:1rem;cursor:pointer;">−</button>
                <span id="doc-zoom-label" style="color:#eee;font-size:0.85rem;min-width:44px;text-align:center;font-family:monospace;">${zoomPct}%</span>
                <button onclick="documentManager.zoomIn()" title="Zoom in (+)"
                        style="background:#444;color:#eee;border:none;border-radius:4px;padding:4px 10px;font-size:1rem;cursor:pointer;">+</button>
                <button onclick="documentManager.zoomFit()" title="Fit to width (0)"
                        style="background:#444;color:#eee;border:none;border-radius:4px;padding:4px 10px;font-size:0.8rem;cursor:pointer;">⟺ Fit</button>
            </div>
            <div id="doc-img-scroll" style="flex:1;overflow:hidden;background:#2a2a3e;position:relative;cursor:grab;">
                <img id="doc-zoom-img"
                     src="/data/documents/${page.filename}"
                     draggable="false"
                     onload="documentManager._onImageLoad(this)"
                     style="position:absolute;border-radius:4px;box-shadow:0 4px 20px rgba(0,0,0,0.5);pointer-events:none;"
                     alt="${page.filename}">
            </div>`;

        this._attachZoomListeners();
    }

    _onImageLoad(img) {
        this._naturalWidth = img.naturalWidth;
        this._naturalHeight = img.naturalHeight;
        this._panX = 0;
        this._panY = 0;
        this.zoomFit();
    }

    _applyTransform() {
        const img = document.getElementById('doc-zoom-img');
        const label = document.getElementById('doc-zoom-label');
        const container = document.getElementById('doc-img-scroll');
        if (!img || !label || !container || !this._naturalWidth) return;

        const W = container.clientWidth;
        const H = container.clientHeight;
        const imgW = Math.round(this._naturalWidth  * this.zoomLevel);
        const imgH = Math.round(this._naturalHeight * this.zoomLevel);

        // Position image: center + pan offset
        img.style.width  = imgW + 'px';
        img.style.height = imgH + 'px';
        img.style.left   = Math.round((W - imgW) / 2 + this._panX) + 'px';
        img.style.top    = Math.round((H - imgH) / 2 + this._panY) + 'px';

        label.textContent = Math.round(this.zoomLevel * 100) + '%';
    }

    zoomIn() {
        const steps = [0.25, 0.33, 0.5, 0.67, 0.75, 1, 1.25, 1.5, 2, 3, 4];
        const next = steps.find(s => s > this.zoomLevel + 0.01);
        this.zoomLevel = next !== undefined ? next : 4;
        this._applyTransform();
    }

    zoomOut() {
        const steps = [0.25, 0.33, 0.5, 0.67, 0.75, 1, 1.25, 1.5, 2, 3, 4];
        const prev = [...steps].reverse().find(s => s < this.zoomLevel - 0.01);
        this.zoomLevel = prev !== undefined ? prev : 0.25;
        this._applyTransform();
    }

    zoomFit() {
        const container = document.getElementById('doc-img-scroll');
        if (container && this._naturalWidth) {
            const scaleW = container.clientWidth  / this._naturalWidth;
            const scaleH = container.clientHeight / this._naturalHeight;
            this.zoomLevel = Math.min(scaleW, scaleH, 1);
        } else {
            this.zoomLevel = 1;
        }
        this._panX = 0;
        this._panY = 0;
        this._applyTransform();
    }

    _attachZoomListeners() {
        const container = document.getElementById('doc-img-scroll');
        if (!container) return;

        // ── Mouse wheel zoom toward cursor ─────────────────────────────────────
        this._wheelHandler = (e) => {
            if (!document.getElementById('doc-zoom-img')) return;
            e.preventDefault();

            const rect = container.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            // Image position before zoom
            const W = container.clientWidth;
            const H = container.clientHeight;
            const imgW_old = this._naturalWidth  * this.zoomLevel;
            const imgH_old = this._naturalHeight * this.zoomLevel;
            const imgLeft  = (W - imgW_old) / 2 + this._panX;
            const imgTop   = (H - imgH_old) / 2 + this._panY;

            // Point on image under cursor (in image pixels)
            const pointX = mouseX - imgLeft;
            const pointY = mouseY - imgTop;

            const oldZoom = this.zoomLevel;
            if (e.deltaY < 0) {
                const steps = [0.25, 0.33, 0.5, 0.67, 0.75, 1, 1.25, 1.5, 2, 3, 4];
                const next = steps.find(s => s > this.zoomLevel + 0.01);
                this.zoomLevel = next !== undefined ? next : 4;
            } else {
                const steps = [0.25, 0.33, 0.5, 0.67, 0.75, 1, 1.25, 1.5, 2, 3, 4];
                const prev = [...steps].reverse().find(s => s < this.zoomLevel - 0.01);
                this.zoomLevel = prev !== undefined ? prev : 0.25;
            }
            const ratio = this.zoomLevel / oldZoom;

            // Adjust pan so pointX/Y stays under cursor
            const imgW_new = this._naturalWidth  * this.zoomLevel;
            const imgH_new = this._naturalHeight * this.zoomLevel;
            const newImgLeft = mouseX - pointX * ratio;
            const newImgTop  = mouseY - pointY * ratio;
            this._panX = newImgLeft - (W - imgW_new) / 2;
            this._panY = newImgTop  - (H - imgH_new) / 2;

            this._applyTransform();
        };
        container.addEventListener('wheel', this._wheelHandler, { passive: false });

        // ── Keyboard zoom ──────────────────────────────────────────────────────
        this._keyHandler = (e) => {
            if (!document.getElementById('doc-zoom-img')) return;
            const tag = document.activeElement?.tagName;
            if (tag === 'INPUT' || tag === 'TEXTAREA') return;
            if (e.key === '+' || e.key === '=') { e.preventDefault(); this.zoomIn(); }
            else if (e.key === '-') { e.preventDefault(); this.zoomOut(); }
            else if (e.key === '0') { e.preventDefault(); this.zoomFit(); }
        };
        document.addEventListener('keydown', this._keyHandler);

        // ── Drag-to-pan ────────────────────────────────────────────────────────
        let isDragging = false;
        let startX, startY, startPanX, startPanY;

        this._panMouseDown = (e) => {
            if (e.button !== 0) return;
            isDragging = true;
            startX    = e.clientX;
            startY    = e.clientY;
            startPanX = this._panX;
            startPanY = this._panY;
            container.style.cursor = 'grabbing';
            e.preventDefault();
        };

        this._panMouseMove = (e) => {
            if (!isDragging) return;
            this._panX = startPanX + (e.clientX - startX);
            this._panY = startPanY + (e.clientY - startY);
            this._applyTransform();
        };

        this._panMouseUp = () => {
            if (!isDragging) return;
            isDragging = false;
            container.style.cursor = 'grab';
        };

        container.addEventListener('mousedown', this._panMouseDown);
        document.addEventListener('mousemove', this._panMouseMove);
        document.addEventListener('mouseup',   this._panMouseUp);
    }

    _removeZoomListeners() {
        const container = document.getElementById('doc-img-scroll');
        if (container && this._wheelHandler)  container.removeEventListener('wheel',     this._wheelHandler);
        if (container && this._panMouseDown)  container.removeEventListener('mousedown', this._panMouseDown);
        if (this._panMouseMove) document.removeEventListener('mousemove', this._panMouseMove);
        if (this._panMouseUp)   document.removeEventListener('mouseup',   this._panMouseUp);
        if (this._keyHandler)   document.removeEventListener('keydown',   this._keyHandler);
        this._wheelHandler = null;
        this._panMouseDown = null;
        this._panMouseMove = null;
        this._panMouseUp   = null;
        this._keyHandler   = null;
    }

    closeDocumentImagePanel() {
        this._removeZoomListeners();
        this.zoomLevel = 1;
        this.currentDocId = null;
        const networkEl  = document.getElementById('network-container');
        const imagePanel = document.getElementById('document-image-panel');
        if (!networkEl || !imagePanel) return;

        imagePanel.style.display = 'none';
        imagePanel.style.flexDirection = '';
        imagePanel.style.alignItems = '';
        imagePanel.style.padding = '';
        networkEl.style.display = 'block';

        // Restore panel header
        const panelHeader = imagePanel.closest('.visualization-panel')?.querySelector('.panel-header h2');
        const viewControls = imagePanel.closest('.visualization-panel')?.querySelector('.view-controls');
        if (panelHeader) panelHeader.textContent = 'Community Network';
        if (viewControls) viewControls.style.display = '';
    }

    prevPage() {
        if (this.currentPageIndex > 0) {
            this.currentPageIndex--;
            this.zoomLevel = 1;
            this._panX = 0;
            this._panY = 0;
            this._naturalWidth = null;
            this._naturalHeight = null;
            this._renderCard();
            this._renderImagePanel();
        }
    }

    nextPage() {
        const doc = this.documents[this.currentDocId];
        if (doc && this.currentPageIndex < doc.pages.length - 1) {
            this.currentPageIndex++;
            this.zoomLevel = 1;
            this._panX = 0;
            this._panY = 0;
            this._naturalWidth = null;
            this._naturalHeight = null;
            this._renderCard();
            this._renderImagePanel();
        }
    }

    // ── Edit document form ─────────────────────────────────────────────────────

    showEditForm(docId) {
        this.editingDocId = docId;
        const doc = this.documents[docId];
        if (!doc) return;

        this._panel().innerHTML = `<div style="padding:15px;">
            <h3 style="margin-top:0;">✏️ Edit Document <span style="font-family:monospace;font-size:0.85rem;color:#999;">${docId}</span></h3>
            <div class="form-group">
                <label>Name</label>
                <input type="text" id="edit-doc-name" value="${doc.name || ''}" style="width:100%;box-sizing:border-box;">
            </div>
            <div class="form-group">
                <label>Year</label>
                <input type="number" id="edit-doc-year" value="${doc.date || ''}" min="1600" max="2100" style="width:100%;box-sizing:border-box;">
            </div>
            <div class="form-group">
                <label>Notes</label>
                <textarea id="edit-doc-notes" rows="3" style="width:100%;box-sizing:border-box;">${doc.notes || ''}</textarea>
            </div>
            <div class="form-group">
                <label>Tags (comma-separated)</label>
                <input type="text" id="edit-doc-tags" value="${(doc.tags || []).join(', ')}" style="width:100%;box-sizing:border-box;">
            </div>
            <div class="form-group">
                <label>External Link</label>
                <input type="text" id="edit-doc-link" value="${doc.link || ''}" style="width:100%;box-sizing:border-box;">
            </div>
            <div class="form-group">
                <label>Linked Events</label>
                <div id="edit-doc-events">${this._renderEditEvents(doc)}</div>
                <div style="display:flex;gap:8px;margin-top:8px;">
                    <input type="text" id="edit-event-id-input" placeholder="Event ID, e.g. E0042"
                           style="flex:1;padding:6px 8px;border:1px solid #ddd;border-radius:4px;"
                           onkeydown="if(event.key==='Enter'){event.preventDefault();documentManager.addEventToEditDoc();}">
                    <button type="button" class="btn-secondary" onclick="documentManager.addEventToEditDoc()">Add</button>
                </div>
            </div>
            <div class="form-group">
                <label>Pages</label>
                <div id="edit-doc-pages">${this._renderEditPages(doc)}</div>
            </div>
            <div style="display:flex;gap:10px;margin-top:20px;">
                <button class="btn-primary" onclick="documentManager.saveEditDocument()">Save Changes</button>
                <button class="btn-secondary" onclick="documentManager.showCard('${docId}')">Cancel</button>
            </div>
        </div>`;
    }

    _renderEditEvents(doc) {
        const events = doc.events || [];
        if (events.length === 0) {
            return '<div style="color:#aaa;font-size:0.85rem;margin-bottom:4px;">No events linked</div>';
        }
        return events.map(eid => {
            const event = this.app.events[eid];
            const label = event
                ? `${eid} — ${event.type}${event.date?.year ? ' ' + event.date.year : ''}`
                : eid;
            return `<div style="display:flex;align-items:center;gap:8px;padding:5px 8px;background:#f0f4ff;border-radius:4px;margin-bottom:4px;font-size:0.88rem;">
                <span style="flex:1;font-family:monospace;">${label}</span>
                <button type="button" style="padding:1px 7px;font-size:0.75rem;color:#c00;border:1px solid #fcc;border-radius:3px;background:#fff8f8;cursor:pointer;"
                        onclick="documentManager.removeEventFromEditDoc('${eid}')">✕</button>
            </div>`;
        }).join('');
    }

    addEventToEditDoc() {
        const input = document.getElementById('edit-event-id-input');
        const eid = input?.value.trim();
        if (!eid) return;
        const doc = this.documents[this.editingDocId];
        if (!doc) return;
        if (!this.app.events[eid]) {
            alert(`Event ${eid} not found in the model.`);
            return;
        }
        if ((doc.events || []).includes(eid)) {
            alert(`Event ${eid} is already linked.`);
            input.value = '';
            return;
        }
        doc.events = [...(doc.events || []), eid];
        document.getElementById('edit-doc-events').innerHTML = this._renderEditEvents(doc);
        input.value = '';
    }

    removeEventFromEditDoc(eid) {
        const doc = this.documents[this.editingDocId];
        if (!doc) return;
        doc.events = (doc.events || []).filter(e => e !== eid);
        document.getElementById('edit-doc-events').innerHTML = this._renderEditEvents(doc);
    }

    _renderEditPages(doc) {
        if (!doc.pages || doc.pages.length === 0) return '<div style="color:#aaa;">No pages</div>';

        return doc.pages.map((page, i) => `
            <div style="border:1px solid #ddd;border-radius:4px;padding:10px;margin-bottom:10px;">
                <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">
                    <span style="font-family:monospace;font-size:0.8rem;flex:1;overflow:hidden;text-overflow:ellipsis;">${page.filename}</span>
                    <button type="button" onclick="documentManager.movePageInEdit(${i},-1)" ${i === 0 ? 'disabled' : ''} style="padding:2px 6px;">↑</button>
                    <button type="button" onclick="documentManager.movePageInEdit(${i},1)" ${i === doc.pages.length - 1 ? 'disabled' : ''} style="padding:2px 6px;">↓</button>
                    <button type="button" class="btn-danger" style="padding:2px 8px;font-size:0.75rem;"
                            onclick="documentManager.deletePageInEdit('${doc.id}','${page.filename}')">✕</button>
                </div>
                <img src="/data/documents/${page.filename}" style="max-width:100%;max-height:120px;object-fit:contain;display:block;margin-bottom:8px;border-radius:2px;">
                <label style="font-size:0.8rem;display:block;margin-bottom:2px;">Transcription:</label>
                <textarea id="page-transcription-${i}" rows="8" style="width:100%;box-sizing:border-box;font-size:0.85rem;resize:vertical;">${page.transcription || ''}</textarea>
            </div>`
        ).join('');
    }

    _readTranscriptionsFromEdit(doc) {
        doc.pages.forEach((page, i) => {
            const el = document.getElementById(`page-transcription-${i}`);
            if (el) page.transcription = el.value;
        });
    }

    movePageInEdit(index, direction) {
        const doc = this.documents[this.editingDocId];
        if (!doc) return;
        const newIndex = index + direction;
        if (newIndex < 0 || newIndex >= doc.pages.length) return;
        this._readTranscriptionsFromEdit(doc);
        [doc.pages[index], doc.pages[newIndex]] = [doc.pages[newIndex], doc.pages[index]];
        document.getElementById('edit-doc-pages').innerHTML = this._renderEditPages(doc);
    }

    async deletePageInEdit(docId, filename) {
        if (!confirm(`Delete page ${filename}? This cannot be undone.`)) return;
        try {
            const res = await fetch('/api/delete-document-page', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ doc_id: docId, filename }),
            });
            const result = await res.json();
            if (result.success) {
                this.documents[docId] = result.document;
                this.app.documents = this.documents;
                document.getElementById('edit-doc-pages').innerHTML = this._renderEditPages(result.document);
            } else {
                alert('Error deleting page: ' + (result.error || 'Unknown error'));
            }
        } catch (e) { alert('Error deleting page: ' + e.message); }
    }

    async saveEditDocument() {
        const doc = this.documents[this.editingDocId];
        if (!doc) return;
        this._readTranscriptionsFromEdit(doc);

        const name    = document.getElementById('edit-doc-name')?.value.trim();
        const yearVal = document.getElementById('edit-doc-year')?.value;
        const notes   = document.getElementById('edit-doc-notes')?.value.trim();
        const tagsRaw = document.getElementById('edit-doc-tags')?.value || '';
        const link    = document.getElementById('edit-doc-link')?.value.trim();
        const tags    = tagsRaw.split(',').map(t => t.trim()).filter(Boolean);

        try {
            const res = await fetch('/api/update-document', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: this.editingDocId,
                    name, date: yearVal ? parseInt(yearVal) : null,
                    notes, tags, link,
                    events: doc.events,
                    pages: doc.pages,
                }),
            });
            const result = await res.json();
            if (result.success) {
                this.documents[this.editingDocId] = result.document;
                this.app.documents = this.documents;
                this.showCard(this.editingDocId);
            } else {
                alert('Error saving: ' + (result.error || 'Unknown error'));
            }
        } catch (e) { alert('Error saving: ' + e.message); }
    }

    // ── Delete document ────────────────────────────────────────────────────────

    async deleteDocument(docId) {
        if (!confirm(`Delete document ${docId} and all its pages? This cannot be undone.`)) return;
        try {
            const res = await fetch('/api/delete-document', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: docId }),
            });
            const result = await res.json();
            if (result.success) {
                delete this.documents[docId];
                this.app.documents = this.documents;
                this.showList();
            } else {
                alert('Error deleting: ' + (result.error || 'Unknown error'));
            }
        } catch (e) { alert('Error deleting: ' + e.message); }
    }

    // ── Event-editor integration ───────────────────────────────────────────────

    // Search documents by name (used by event editor)
    searchByName(query) {
        query = (query || '').toLowerCase();
        return Object.values(this.documents).filter(doc =>
            (doc.name || '').toLowerCase().includes(query)
        );
    }

    // Link a document to an event (adds eventId to doc.events)
    async linkDocumentToEvent(docId, eventId) {
        const doc = this.documents[docId];
        if (!doc) return false;
        if (doc.events.includes(eventId)) return true; // already linked

        const updatedEvents = [...doc.events, eventId];
        try {
            const res = await fetch('/api/update-document', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...doc, events: updatedEvents }),
            });
            const result = await res.json();
            if (result.success) {
                this.documents[docId] = result.document;
                this.app.documents = this.documents;
                return true;
            }
        } catch (e) { console.error('linkDocumentToEvent:', e); }
        return false;
    }

    // Unlink a document from an event
    async unlinkDocumentFromEvent(docId, eventId) {
        const doc = this.documents[docId];
        if (!doc) return false;

        const updatedEvents = doc.events.filter(e => e !== eventId);
        try {
            const res = await fetch('/api/update-document', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...doc, events: updatedEvents }),
            });
            const result = await res.json();
            if (result.success) {
                this.documents[docId] = result.document;
                this.app.documents = this.documents;
                return true;
            }
        } catch (e) { console.error('unlinkDocumentFromEvent:', e); }
        return false;
    }
}

