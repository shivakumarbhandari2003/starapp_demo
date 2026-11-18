/**
 * STAR APP DATABASE MIND MAP — SEARCH ENGINE
 * Indexes modules, submodules, tables, and columns.
 * Supports progressive expansion, navigation, and highlighting.
 */
(function() {
  class MindmapSearch {
    constructor(inputEl, resultsContainerEl) {
      this.inputEl = inputEl;
      this.resultsContainerEl = resultsContainerEl;
      this.searchIndex = [];
      this.onResultSelected = null;
      this.selectedIndex = -1;
      this.currentResults = [];

      this._buildSearchIndex();
      this._bindEvents();
    }

    _buildSearchIndex() {
      const schema = window.STAR_APP_SCHEMA;
      if (!schema) return;

      // 1. Index Modules
      schema.modules.forEach(m => {
        this.searchIndex.push({
          type: 'module',
          id: m.id,
          name: m.name,
          title: `Module ${m.num}: ${m.name}`,
          breadcrumb: 'Root Database',
          meta: `${m.submodules.length} Submodules`,
          color: m.color,
          nodeId: m.id
        });

        // 2. Index Submodules
        m.submodules.forEach(sub => {
          this.searchIndex.push({
            type: 'submodule',
            id: sub.id,
            name: sub.name,
            title: sub.name,
            breadcrumb: m.name,
            meta: `${sub.tables.length} Tables`,
            color: m.color,
            nodeId: sub.id,
            parentId: m.id
          });

          // 3. Index Tables
          sub.tables.forEach(tName => {
            const table = schema.tables[tName];
            if (!table) return;

            this.searchIndex.push({
              type: 'table',
              id: `table_${tName}`,
              tableName: tName,
              name: tName,
              title: `TABLE: ${tName} (#${table.table_number})`,
              breadcrumb: `${m.name} > ${sub.name}`,
              meta: `${table.columns.length} Columns`,
              color: m.color,
              nodeId: `table_${tName}`,
              parentId: sub.id
            });

            // 4. Index Columns
            table.columns.forEach(col => {
              const keyDesc = col.is_pk ? 'PK' : (col.is_fk ? 'FK' : (col.is_derived ? 'DERIVED' : 'Column'));
              this.searchIndex.push({
                type: 'column',
                id: `col_${tName}_${col.name}`,
                columnName: col.name,
                tableName: tName,
                name: col.name,
                title: `${col.name} (${keyDesc})`,
                breadcrumb: `${tName} [${sub.name}]`,
                meta: col.references ? `➔ ${col.references}` : keyDesc,
                color: m.color,
                nodeId: `col_${tName}_${col.name}`,
                parentId: `table_${tName}`,
                tableNodeId: `table_${tName}`
              });
            });
          });
        });
      });
    }

    _bindEvents() {
      if (!this.inputEl || !this.resultsContainerEl) return;

      this.inputEl.addEventListener('input', (e) => {
        const query = e.target.value.trim().toLowerCase();
        if (query.length === 0) {
          this.clearResults();
          return;
        }
        this._search(query);
      });

      this.inputEl.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          this._navigateResults(1);
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          this._navigateResults(-1);
        } else if (e.key === 'Enter') {
          e.preventDefault();
          if (this.selectedIndex >= 0 && this.selectedIndex < this.currentResults.length) {
            this._selectItem(this.currentResults[this.selectedIndex]);
          } else if (this.currentResults.length > 0) {
            this._selectItem(this.currentResults[0]);
          }
        } else if (e.key === 'Escape') {
          this.clearResults();
          this.inputEl.blur();
        }
      });

      document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-box-wrapper')) {
          this.clearResults();
        }
      });
    }

    _search(query) {
      const q = query.toLowerCase();
      const scored = [];

      this.searchIndex.forEach(item => {
        const nameLower = item.name.toLowerCase();
        let score = 0;

        if (nameLower === q) score += 100;
        else if (nameLower.startsWith(q)) score += 60;
        else if (nameLower.includes(q)) score += 30;
        else if (item.breadcrumb.toLowerCase().includes(q)) score += 10;

        // Boost tables and primary keys
        if (item.type === 'table') score += 15;
        if (item.type === 'column' && item.meta.includes('PK')) score += 8;

        if (score > 0) {
          scored.push({ item, score });
        }
      });

      scored.sort((a, b) => b.score - a.score);
      this.currentResults = scored.slice(0, 15).map(s => s.item);
      this.selectedIndex = -1;
      this._renderDropdown();
    }

    _renderDropdown() {
      const rc = this.resultsContainerEl;
      if (this.currentResults.length === 0) {
        rc.innerHTML = '<div class="search-empty">No database elements found matching your search.</div>';
        rc.classList.add('visible');
        return;
      }

      let html = '';
      this.currentResults.forEach((item, idx) => {
        const typeBadgeClass = `badge-search-${item.type}`;
        html += `
          <div class="search-item ${idx === this.selectedIndex ? 'selected' : ''}" data-search-idx="${idx}">
            <div class="search-item-header">
              <span class="search-type-badge ${typeBadgeClass}">${item.type.toUpperCase()}</span>
              <span class="search-item-title">${item.title}</span>
            </div>
            <div class="search-item-meta">
              <span class="search-breadcrumb">${item.breadcrumb}</span>
              <span class="search-item-detail">${item.meta}</span>
            </div>
          </div>
        `;
      });

      rc.innerHTML = html;
      rc.classList.add('visible');

      rc.querySelectorAll('.search-item').forEach(el => {
        el.addEventListener('click', () => {
          const idx = parseInt(el.getAttribute('data-search-idx'), 10);
          this._selectItem(this.currentResults[idx]);
        });
      });
    }

    _navigateResults(dir) {
      if (this.currentResults.length === 0) return;
      this.selectedIndex += dir;
      if (this.selectedIndex < 0) this.selectedIndex = this.currentResults.length - 1;
      if (this.selectedIndex >= this.currentResults.length) this.selectedIndex = 0;

      const items = this.resultsContainerEl.querySelectorAll('.search-item');
      items.forEach((el, idx) => {
        if (idx === this.selectedIndex) {
          el.classList.add('selected');
          el.scrollIntoView({ block: 'nearest' });
        } else {
          el.classList.remove('selected');
        }
      });
    }

    _selectItem(item) {
      this.clearResults();
      this.inputEl.value = item.name;
      if (this.onResultSelected) {
        this.onResultSelected(item);
      }
    }

    clearResults() {
      this.resultsContainerEl.classList.remove('visible');
      this.resultsContainerEl.innerHTML = '';
      this.currentResults = [];
      this.selectedIndex = -1;
    }
  }

  window.STAR_APP_SEARCH = MindmapSearch;
})();
