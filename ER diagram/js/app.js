/**
 * STAR APP DATABASE MIND MAP — APPLICATION CONTROLLER (ENHANCED)
 * Orchestrates tree structure, state, layout, rendering, and UI interactions.
 */
(function() {
  class StarAppMindMap {
    constructor() {
      this.schema = window.STAR_APP_SCHEMA;
      this.relationships = window.STAR_APP_RELATIONSHIPS;

      // Tree root
      this.treeRoot = null;
      this.parentMap = new Map(); // childId -> parentId
      this.nodeLookup = new Map(); // id -> node

      // State
      this.expansionState = new Map();
      this.relMode = 'all'; // 'selected' (focused on active table), 'all' (all visible), 'none' (off)
      this.selectedTable = null;
      this.hoveredTable = null;
      this.activeNodeId = null;
      this.allAttributesExpanded = true;

      // Modules
      this.layoutEngine = new window.STAR_APP_LAYOUT_ENGINE();
      this.renderer = null;
      this.interactions = null;
      this.search = null;

      this._init();
    }

    _init() {
      this._buildCompleteTree();
      this._setupInitialExpansion();
      this._setupComponents();
      this._bindGlobalControls();
      this._bindKeyboardShortcuts();

      // Initial render & fit
      this.updateView(true);
      setTimeout(() => {
        this.interactions.fitToScreen();
      }, 120);
    }

    _buildCompleteTree() {
      const schema = this.schema;

      // 1. Root Node
      this.treeRoot = {
        id: 'root',
        type: 'root',
        name: schema.rootName || 'STAR APP DATABASE',
        color: '#6366F1',
        children: []
      };
      this.nodeLookup.set('root', this.treeRoot);

      // 2. Modules
      schema.modules.forEach(m => {
        const modNode = {
          id: m.id,
          type: 'module',
          name: m.name,
          num: m.num,
          color: m.color,
          raw: m,
          children: []
        };
        this.treeRoot.children.push(modNode);
        this.nodeLookup.set(m.id, modNode);
        this.parentMap.set(m.id, 'root');

        // 3. Submodules
        m.submodules.forEach(sub => {
          const subNode = {
            id: sub.id,
            type: 'submodule',
            name: sub.name,
            color: m.color,
            raw: sub,
            children: []
          };
          modNode.children.push(subNode);
          this.nodeLookup.set(sub.id, subNode);
          this.parentMap.set(sub.id, m.id);

          // 4. Tables (Attributes are rendered inside the table card)
          sub.tables.forEach(tName => {
            const tData = schema.tables[tName];
            if (!tData) return;

            const tableId = `table_${tName}`;
            const tableNode = {
              id: tableId,
              type: 'table',
              name: tName,
              tableName: tName,
              color: m.color,
              raw: tData,
              children: [] // leaf node in tree hierarchy; columns are embedded in card
            };
            subNode.children.push(tableNode);
            this.nodeLookup.set(tableId, tableNode);
            this.parentMap.set(tableId, sub.id);
          });
        });
      });
    }

    _setupInitialExpansion() {
      this.expansionState.clear();
      // Expand root and all structural nodes + all table cards
      this.nodeLookup.forEach((node, id) => {
        this.expansionState.set(id, true);
      });
      this.allAttributesExpanded = true;
    }

    _setupComponents() {
      const canvasEl = document.getElementById('mindmap-canvas');
      const svgEl = document.getElementById('mindmap-svg');
      const nodesContainerEl = document.getElementById('mindmap-nodes');
      const viewportEl = document.getElementById('mindmap-viewport');
      const minimapCanvasEl = document.getElementById('minimap-canvas');
      const detailDrawerEl = document.getElementById('table-detail-drawer');
      const searchInputEl = document.getElementById('mindmap-search-input');
      const searchResultsEl = document.getElementById('search-dropdown');

      // Renderer
      this.renderer = new window.STAR_APP_RENDERER(canvasEl, svgEl, nodesContainerEl);
      this.renderer.onToggleExpand = (nodeId) => this.toggleNode(nodeId);
      this.renderer.onSelectNode = (node) => this.selectNode(node);
      this.renderer.onNavigateFK = (targetTable) => this.navigateToTable(targetTable);
      this.renderer.onHoverNode = (tableName) => this.hoverTable(tableName);
      this.renderer.onOpenDrawer = (tableName) => {
        const tableNode = Array.from(this.nodeLookup.values()).find(n => n.type === 'table' && n.name === tableName);
        if (tableNode) {
          this.selectedTable = tableName;
          this.activeNodeId = tableNode.id;
        }
        this.interactions.openTableDrawer(tableName);
      };

      // Interactions
      this.interactions = new window.STAR_APP_INTERACTIONS(viewportEl, canvasEl, minimapCanvasEl, detailDrawerEl);
      this.interactions.onNavigateTable = (targetTable) => this.navigateToTable(targetTable);

      // Search
      this.search = new window.STAR_APP_SEARCH(searchInputEl, searchResultsEl);
      this.search.onResultSelected = (item) => this.handleSearchResult(item);
    }

    _bindGlobalControls() {
      // Expand All
      document.getElementById('btn-expand-all').addEventListener('click', () => {
        this.expandAll(true);
      });

      // Collapse All
      document.getElementById('btn-collapse-all').addEventListener('click', () => {
        this.collapseAll();
      });

      // Toggle In-Card Attributes on all tables
      const btnToggleAttrs = document.getElementById('btn-toggle-attrs');
      if (btnToggleAttrs) {
        // Initial state: all expanded
        btnToggleAttrs.classList.add('active');
        btnToggleAttrs.querySelector('.btn-label').textContent = 'Hide Card Attributes';

        btnToggleAttrs.addEventListener('click', () => {
          this.allAttributesExpanded = !this.allAttributesExpanded;
          this.nodeLookup.forEach((node, id) => {
            if (node.type === 'table') {
              this.expansionState.set(id, this.allAttributesExpanded);
            }
          });
          btnToggleAttrs.classList.toggle('active', this.allAttributesExpanded);
          btnToggleAttrs.querySelector('.btn-label').textContent = this.allAttributesExpanded ? 'Hide Card Attributes' : 'Show Card Attributes';
          this.updateView(true);
          setTimeout(() => this.interactions.fitToScreen(), 150);
        });
      }

      // Relationship Display Mode Toggle (Cycles through: Selected Table Only ➔ All Relationships ➔ Off)
      const relToggleBtn = document.getElementById('btn-toggle-rels');
      if (relToggleBtn) {
        relToggleBtn.addEventListener('click', () => {
          if (this.relMode === 'selected') {
            this.relMode = 'all';
            relToggleBtn.classList.add('active');
            relToggleBtn.querySelector('.btn-label').textContent = 'Relationships: All (42 Lines)';
          } else if (this.relMode === 'all') {
            this.relMode = 'none';
            relToggleBtn.classList.remove('active');
            relToggleBtn.querySelector('.btn-label').textContent = 'Relationships: Off';
          } else {
            this.relMode = 'selected';
            relToggleBtn.classList.add('active');
            relToggleBtn.querySelector('.btn-label').textContent = 'Relationships: Focused';
          }
          this.updateView(false);
        });
      }

      // Zoom controls
      document.getElementById('btn-zoom-in').addEventListener('click', () => this.interactions.zoomIn());
      document.getElementById('btn-zoom-out').addEventListener('click', () => this.interactions.zoomOut());
      document.getElementById('btn-fit-screen').addEventListener('click', () => this.interactions.fitToScreen());
      document.getElementById('btn-reset-view').addEventListener('click', () => this.interactions.resetView());

      // Orientation toggle
      const btnOrient = document.getElementById('btn-toggle-orient');
      if (btnOrient) {
        btnOrient.querySelector('.btn-label').textContent = this.layoutEngine.orientation === 'TB' ? 'Vertical (T➔B)' : 'Horizontal (L➔R)';
        btnOrient.addEventListener('click', () => {
          const current = this.layoutEngine.orientation;
          const next = current === 'TB' ? 'LR' : 'TB';
          this.layoutEngine.setOrientation(next);
          btnOrient.querySelector('.btn-label').textContent = next === 'TB' ? 'Vertical (T➔B)' : 'Horizontal (L➔R)';
          this.updateView(true);
          setTimeout(() => this.interactions.fitToScreen(), 150);
        });
      }
    }

    _bindKeyboardShortcuts() {
      window.addEventListener('keydown', (e) => {
        if ((e.key === '/' || (e.ctrlKey && e.key === 'f')) && document.activeElement !== document.getElementById('mindmap-search-input')) {
          e.preventDefault();
          document.getElementById('mindmap-search-input').focus();
        }
      });
    }

    toggleNode(nodeId, forceState = null) {
      const isExpanded = this.expansionState.get(nodeId) === true;
      const nextState = forceState !== null ? forceState : !isExpanded;
      this.expansionState.set(nodeId, nextState);

      const node = this.nodeLookup.get(nodeId);
      if (node && node.type === 'table') {
        this.selectedTable = node.name;
        this.activeNodeId = nodeId;
      }
      this.updateView(false);
    }

    selectNode(node) {
      this.activeNodeId = node.id;
      if (node.type === 'table') {
        this.selectedTable = node.name;
        this.interactions.openTableDrawer(node.name);
      }
      this.updateView(false);
    }

    hoverTable(tableName) {
      this.hoveredTable = tableName;
      this.renderer.render(this.lastLayoutResult, {
        relMode: this.relMode,
        selectedTable: this.selectedTable,
        hoveredTable: this.hoveredTable
      });
    }

    expandAll(includeAttributes = true) {
      this.nodeLookup.forEach((node, id) => {
        if (node.type === 'table') {
          this.expansionState.set(id, includeAttributes);
        } else {
          this.expansionState.set(id, true);
        }
      });
      this.allAttributesExpanded = includeAttributes;
      const btnToggleAttrs = document.getElementById('btn-toggle-attrs');
      if (btnToggleAttrs) {
        btnToggleAttrs.classList.toggle('active', includeAttributes);
        btnToggleAttrs.querySelector('.btn-label').textContent = includeAttributes ? 'Hide Card Attributes' : 'Show Card Attributes';
      }
      this.updateView(true);
      setTimeout(() => this.interactions.fitToScreen(), 200);
    }

    collapseAll() {
      this.expansionState.clear();
      this.expansionState.set('root', true);
      this.selectedTable = null;
      this.activeNodeId = null;
      this.allAttributesExpanded = true;
      const btnToggleAttrs = document.getElementById('btn-toggle-attrs');
      if (btnToggleAttrs) {
        btnToggleAttrs.classList.remove('active');
        btnToggleAttrs.querySelector('.btn-label').textContent = 'Show Card Attributes';
      }
      this.interactions.closeDrawer();
      this.updateView(true);
      setTimeout(() => this.interactions.fitToScreen(), 200);
    }

    expandAncestorsOf(nodeId) {
      let currentId = nodeId;
      while (currentId) {
        const parentId = this.parentMap.get(currentId);
        if (parentId) {
          this.expansionState.set(parentId, true);
        }
        currentId = parentId;
      }
    }

    navigateToTable(tableName) {
      const tableId = `table_${tableName}`;
      this.expandAncestorsOf(tableId);
      // Also expand attributes of the target table so user can read them immediately!
      this.expansionState.set(tableId, true);
      this.selectedTable = tableName;
      this.activeNodeId = tableId;

      this.updateView(false);

      const targetPosNode = this.renderer.tableNodeMap.get(tableName);
      if (targetPosNode) {
        this.interactions.centerOnNode(targetPosNode);
        this._highlightNodePulse(tableId);
      }

      this.interactions.openTableDrawer(tableName);
    }

    handleSearchResult(item) {
      const targetTableId = item.type === 'column' ? `table_${item.tableName}` : item.nodeId;
      this.expandAncestorsOf(targetTableId);
      
      // Expand target table card to reveal attributes
      this.expansionState.set(targetTableId, true);

      if (item.type === 'table' || item.type === 'column') {
        this.selectedTable = item.tableName;
      }
      this.activeNodeId = targetTableId;

      this.updateView(false);

      const targetPosNode = this.renderer.tableNodeMap.get(item.tableName) || this.renderer.nodeMap.get(item.nodeId);
      if (targetPosNode) {
        this.interactions.centerOnNode(targetPosNode);
        this._highlightNodePulse(targetTableId);
      }

      if (item.type === 'table' || item.type === 'column') {
        this.interactions.openTableDrawer(item.tableName);
      }
    }

    _highlightNodePulse(nodeId) {
      setTimeout(() => {
        const el = document.getElementById(`node-${nodeId}`);
        if (el) {
          el.classList.add('node-pulse-highlight');
          setTimeout(() => el.classList.remove('node-pulse-highlight'), 1800);
        }
      }, 50);
    }

    updateView(shouldFit = false) {
      // 1. Calculate dynamic layout with in-card heights
      const layoutResult = this.layoutEngine.computeLayout(this.treeRoot, this.expansionState);
      this.lastLayoutResult = layoutResult;

      // 2. Adjust SVG layer size to bounds
      const svgEl = document.getElementById('mindmap-svg');
      const extraPad = 600;
      svgEl.setAttribute('width', `${Math.max(1400, layoutResult.bounds.maxX + extraPad)}`);
      svgEl.setAttribute('height', `${Math.max(900, layoutResult.bounds.maxY + extraPad)}`);

      // 3. Render SVG connectors & DOM nodes
      this.renderer.render(layoutResult, {
        relMode: this.relMode,
        selectedTable: this.selectedTable,
        hoveredTable: this.hoveredTable,
        orientation: this.layoutEngine.orientation
      });

      // 4. Update Minimap
      this.interactions.updateMinimapData(layoutResult.bounds, layoutResult.nodes);

      // 5. Update stats count in toolbar
      this._updateToolbarStats(layoutResult);

      if (shouldFit) {
        this.interactions.fitToScreen(layoutResult.bounds);
      }
    }

    _updateToolbarStats(layoutResult) {
      const statsEl = document.getElementById('canvas-stats-badge');
      if (!statsEl) return;

      const visibleTables = layoutResult.nodes.filter(n => n.type === 'table').length;
      const expandedTables = layoutResult.nodes.filter(n => n.type === 'table' && n.isExpanded).length;

      statsEl.innerHTML = `
        <span><strong>${visibleTables}</strong> / 29 Tables</span> &bull; 
        <span><strong>${expandedTables}</strong> Expanded</span>
      `;
    }
  }

  // Initialize on DOM ready
  window.addEventListener('DOMContentLoaded', () => {
    window.starAppMindMapInstance = new StarAppMindMap();
    const params = new URLSearchParams(window.location.search);
    const focusTable = params.get('table');
    if (focusTable) {
      setTimeout(() => {
        window.starAppMindMapInstance.navigateToTable(focusTable);
      }, 250);
    }
  });
})();
