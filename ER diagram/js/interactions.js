/**
 * STAR APP DATABASE MIND MAP — INTERACTIONS
 * Manages viewport pan/zoom, minimap, table detail side drawer, and expansion state.
 */
(function() {
  class MindmapInteractions {
    constructor(viewportEl, canvasEl, minimapCanvasEl, detailDrawerEl) {
      this.viewportEl = viewportEl;
      this.canvasEl = canvasEl;
      this.minimapCanvasEl = minimapCanvasEl;
      this.detailDrawerEl = detailDrawerEl;

      // Transform state
      this.transform = {
        x: 60,
        y: 100,
        scale: 0.85
      };

      // Drag/Pan state
      this.isPanning = false;
      this.startX = 0;
      this.startY = 0;

      // Minimap state
      this.minimapCtx = minimapCanvasEl ? minimapCanvasEl.getContext('2d') : null;
      this.currentBounds = { minX: 0, minY: 0, maxX: 1000, maxY: 1000, width: 1000, height: 1000 };
      this.currentNodes = [];

      // Callbacks
      this.onTransformChange = null;
      this.onNavigateTable = null;

      this._initPanZoom();
      this._initDrawerEvents();
    }

    _initPanZoom() {
      const vp = this.viewportEl;

      // Mouse drag to pan
      vp.addEventListener('mousedown', (e) => {
        // Only pan if clicking on empty viewport or background canvas, not on a node or button
        if (e.target.closest('.mindmap-node') || e.target.closest('button') || e.target.closest('#table-detail-drawer')) {
          return;
        }
        this.isPanning = true;
        this.startX = e.clientX - this.transform.x;
        this.startY = e.clientY - this.transform.y;
        vp.style.cursor = 'grabbing';
      });

      window.addEventListener('mousemove', (e) => {
        if (!this.isPanning) return;
        this.transform.x = e.clientX - this.startX;
        this.transform.y = e.clientY - this.startY;
        this.applyTransform();
      });

      window.addEventListener('mouseup', () => {
        if (this.isPanning) {
          this.isPanning = false;
          vp.style.cursor = 'grab';
        }
      });

      // Mouse wheel zoom
      vp.addEventListener('wheel', (e) => {
        e.preventDefault();
        const rect = vp.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const zoomFactor = e.deltaY < 0 ? 1.12 : 0.89;
        const newScale = Math.min(2.5, Math.max(0.12, this.transform.scale * zoomFactor));

        // Zoom relative to mouse cursor
        this.transform.x = mouseX - (mouseX - this.transform.x) * (newScale / this.transform.scale);
        this.transform.y = mouseY - (mouseY - this.transform.y) * (newScale / this.transform.scale);
        this.transform.scale = newScale;

        this.applyTransform();
      }, { passive: false });
    }

    applyTransform(smooth = false) {
      if (smooth) {
        this.canvasEl.style.transition = 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
        setTimeout(() => {
          this.canvasEl.style.transition = 'none';
        }, 400);
      } else {
        this.canvasEl.style.transition = 'none';
      }

      this.canvasEl.style.transform = `translate(${this.transform.x}px, ${this.transform.y}px) scale(${this.transform.scale})`;

      this.updateMinimap();

      if (this.onTransformChange) {
        this.onTransformChange(this.transform);
      }
    }

    zoomIn() {
      this._zoomBy(1.25);
    }

    zoomOut() {
      this._zoomBy(0.8);
    }

    _zoomBy(factor) {
      const rect = this.viewportEl.getBoundingClientRect();
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      const newScale = Math.min(2.5, Math.max(0.12, this.transform.scale * factor));
      this.transform.x = centerX - (centerX - this.transform.x) * (newScale / this.transform.scale);
      this.transform.y = centerY - (centerY - this.transform.y) * (newScale / this.transform.scale);
      this.transform.scale = newScale;

      this.applyTransform(true);
    }

    resetView() {
      const vpRect = this.viewportEl.getBoundingClientRect();
      this.transform.x = 80;
      this.transform.y = Math.max(40, vpRect.height / 2 - 200);
      this.transform.scale = 0.85;
      this.applyTransform(true);
    }

    fitToScreen(bounds) {
      if (!bounds) bounds = this.currentBounds;
      const vpRect = this.viewportEl.getBoundingClientRect();
      const padding = 80;

      const availableW = Math.max(200, vpRect.width - padding * 2);
      const availableH = Math.max(200, vpRect.height - padding * 2);

      const scaleX = availableW / (bounds.width || 800);
      const scaleY = availableH / (bounds.height || 600);
      let fitScale = Math.min(scaleX, scaleY);
      fitScale = Math.min(1.2, Math.max(0.08, fitScale));

      this.transform.scale = fitScale;
      this.transform.x = padding - bounds.minX * fitScale + (availableW - bounds.width * fitScale) / 2;
      this.transform.y = padding - bounds.minY * fitScale + (availableH - bounds.height * fitScale) / 2;

      this.applyTransform(true);
    }

    centerOnNode(node) {
      if (!node) return;
      const vpRect = this.viewportEl.getBoundingClientRect();
      const targetScale = Math.max(0.8, this.transform.scale);

      this.transform.scale = targetScale;
      this.transform.x = vpRect.width / 2 - (node.x + node.width / 2) * targetScale;
      this.transform.y = vpRect.height / 2 - (node.y + node.height / 2) * targetScale;

      this.applyTransform(true);
    }

    // Minimap Rendering
    updateMinimapData(bounds, nodes) {
      this.currentBounds = bounds;
      this.currentNodes = nodes;
      this.updateMinimap();
    }

    updateMinimap() {
      if (!this.minimapCtx || !this.minimapCanvasEl) return;
      const ctx = this.minimapCtx;
      const cv = this.minimapCanvasEl;
      const w = cv.width;
      const h = cv.height;

      ctx.clearRect(0, 0, w, h);

      // Background
      ctx.fillStyle = '#0F172A';
      ctx.fillRect(0, 0, w, h);

      const b = this.currentBounds;
      const padding = 20;
      const scaleX = (w - padding * 2) / Math.max(100, b.width);
      const scaleY = (h - padding * 2) / Math.max(100, b.height);
      const mScale = Math.min(scaleX, scaleY);

      const mapX = (x) => padding + (x - b.minX) * mScale;
      const mapY = (y) => padding + (y - b.minY) * mScale;

      // Draw nodes as dots/bars
      this.currentNodes.forEach(node => {
        const nx = mapX(node.x);
        const ny = mapY(node.y);
        const nw = Math.max(3, node.width * mScale);
        const nh = Math.max(2, node.height * mScale);

        ctx.fillStyle = node.color || '#3B82F6';
        if (node.type === 'table') {
          ctx.fillStyle = '#10B981';
        } else if (node.type === 'root') {
          ctx.fillStyle = '#EC4899';
        }
        ctx.fillRect(nx, ny, nw, nh);
      });

      // Draw visible viewport rectangle
      const vpRect = this.viewportEl.getBoundingClientRect();
      const vpLeft = (-this.transform.x) / this.transform.scale;
      const vpTop = (-this.transform.y) / this.transform.scale;
      const vpWidth = vpRect.width / this.transform.scale;
      const vpHeight = vpRect.height / this.transform.scale;

      const rX = mapX(vpLeft);
      const rY = mapY(vpTop);
      const rW = vpWidth * mScale;
      const rH = vpHeight * mScale;

      ctx.strokeStyle = '#38BDF8';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(rX, rY, rW, rH);
      ctx.fillStyle = 'rgba(56, 189, 248, 0.12)';
      ctx.fillRect(rX, rY, rW, rH);
    }

    // Detail Side Drawer
    _initDrawerEvents() {
      if (!this.detailDrawerEl) return;
      const closeBtn = this.detailDrawerEl.querySelector('.drawer-close-btn');
      if (closeBtn) {
        closeBtn.addEventListener('click', () => {
          this.closeDrawer();
        });
      }

      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.detailDrawerEl.classList.contains('open')) {
          this.closeDrawer();
        }
      });
    }

    openTableDrawer(tableName) {
      if (!this.detailDrawerEl) return;
      try {
        const tableData = window.STAR_APP_SCHEMA && window.STAR_APP_SCHEMA.tables ? window.STAR_APP_SCHEMA.tables[tableName] : null;
        if (!tableData) {
          console.warn('Table not found in schema:', tableName);
          return;
        }

        const relHelpers = window.STAR_APP_RELATIONSHIP_HELPERS;
        const incomingRels = relHelpers ? relHelpers.getIncoming(tableName) : [];
        const outgoingRels = relHelpers ? relHelpers.getOutgoing(tableName) : [];

        const contentEl = this.detailDrawerEl.querySelector('.drawer-body');
        const titleEl = this.detailDrawerEl.querySelector('.drawer-title');
        const subtitleEl = this.detailDrawerEl.querySelector('.drawer-subtitle');

        if (titleEl) {
          titleEl.innerHTML = `
            <span class="table-num-badge">#${tableData.table_number || ''}</span>
            ${tableData.name}
          `;
        }

        if (subtitleEl) {
          const modInfo = tableData.module_info || {};
          subtitleEl.innerHTML = `
            <span class="mod-pill" style="background:${modInfo.module_color || '#3B82F6'}">${modInfo.module_name || 'Module'}</span>
            &bull; <span>${modInfo.submodule_name || ''}</span>
          `;
        }

        // Columns list
        const cols = tableData.columns || [];
        const colsHtml = cols.map(col => {
          let tag = '';
          if (col.is_pk) tag = '<span class="badge-tag pk-tag">PK</span>';
          else if (col.is_fk) tag = '<span class="badge-tag fk-tag">FK</span>';
          else if (col.is_derived) tag = '<span class="badge-tag derived-tag">DERIVED</span>';

          let refHtml = '';
          if (col.references) {
            const refTarget = col.references.split('.')[0];
            refHtml = `<span class="col-ref-pill" data-jump-table="${refTarget}" title="Navigate to ${col.references}">➔ ${col.references}</span>`;
          }

          return `
            <tr class="${col.is_pk ? 'row-pk' : (col.is_fk ? 'row-fk' : '')}">
              <td style="width: 70px;">${tag || '<span class="badge-tag regular-tag">-</span>'}</td>
              <td><strong>${col.name}</strong></td>
              <td>${refHtml || (col.is_unique ? '<span class="unique-pill">UNIQUE</span>' : '<span class="text-muted">attribute</span>')}</td>
            </tr>
          `;
        }).join('');

        // Notes list
        const notesHtml = tableData.notes && tableData.notes.length > 0 ? `
          <div class="drawer-section">
            <h4 class="section-heading">Business Rules & Integrity Notes</h4>
            <ul class="drawer-notes-list">
              ${tableData.notes.map(n => `<li>${n}</li>`).join('')}
            </ul>
          </div>
        ` : '';

        // Relationships
        const renderRelItem = (r, dir) => {
          const otherTable = dir === 'out' ? r.target : r.source;
          return `
            <div class="rel-drawer-card" data-jump-table="${otherTable}">
              <div class="rel-drawer-header">
                <span class="rel-dir-badge">${dir === 'out' ? '➔ Outgoing' : '⬅ Incoming'}</span>
                <span class="rel-cardinality-badge">${r.cardinality}</span>
                <span class="rel-other-table">${otherTable}</span>
              </div>
              <div class="rel-drawer-desc">${r.description}</div>
              <div class="rel-drawer-fk">Foreign Key: <code>${r.foreign_key || 'id reference'}</code></div>
            </div>
          `;
        };

        const outRelsHtml = outgoingRels.map(r => renderRelItem(r, 'out')).join('');
        const inRelsHtml = incomingRels.map(r => renderRelItem(r, 'in')).join('');

        if (contentEl) {
          contentEl.innerHTML = `
            <div class="drawer-section">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <h4 class="section-heading" style="margin:0;">Columns & Key Constraints (${cols.length})</h4>
                <button type="button" class="btn-focus-table" id="btn-focus-in-map" title="Center on map">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>
                  Focus in Mind Map
                </button>
              </div>
              <table class="drawer-schema-table">
                <thead>
                  <tr>
                    <th>Key</th>
                    <th>Column Name</th>
                    <th>Constraint / Target</th>
                  </tr>
                </thead>
                <tbody>
                  ${colsHtml}
                </tbody>
              </table>
            </div>

            ${notesHtml}

            <div class="drawer-section">
              <h4 class="section-heading">Foreign Key Relationships (${outgoingRels.length + incomingRels.length})</h4>
              ${outgoingRels.length > 0 ? `
                <div class="rel-subheading">Outgoing Relationships (${outgoingRels.length}):</div>
                ${outRelsHtml}
              ` : ''}
              ${incomingRels.length > 0 ? `
                <div class="rel-subheading" style="margin-top:14px;">Incoming Relationships (${incomingRels.length}):</div>
                ${inRelsHtml}
              ` : ''}
              ${outgoingRels.length === 0 && incomingRels.length === 0 ? '<div class="text-muted">No foreign key relationships found.</div>' : ''}
            </div>
          `;

          // Attach jump links inside drawer
          contentEl.querySelectorAll('[data-jump-table]').forEach(el => {
            el.addEventListener('click', () => {
              const target = el.getAttribute('data-jump-table');
              if (this.onNavigateTable) {
                this.onNavigateTable(target);
              }
            });
          });

          // Attach focus button
          const focusBtn = contentEl.querySelector('#btn-focus-in-map');
          if (focusBtn) {
            focusBtn.addEventListener('click', () => {
              if (this.onNavigateTable) {
                this.onNavigateTable(tableName);
              }
            });
          }

          contentEl.scrollTop = 0;
        }

        this.detailDrawerEl.classList.add('open');
        this.detailDrawerEl.style.display = 'flex';
        this.detailDrawerEl.style.transform = 'translateX(0)';
      } catch (err) {
        console.error('Error opening table drawer for:', tableName, err);
      }
    }

    closeDrawer() {
      if (this.detailDrawerEl) {
        this.detailDrawerEl.classList.remove('open');
        this.detailDrawerEl.style.transform = '';
      }
    }
  }

  window.STAR_APP_INTERACTIONS = MindmapInteractions;
})();
