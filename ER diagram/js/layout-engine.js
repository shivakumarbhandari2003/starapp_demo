/**
 * STAR APP DATABASE MIND MAP — DYNAMIC LAYOUT ENGINE (ENHANCED)
 * Computes dynamic node dimensions, in-card attribute expansion,
 * and recursive collision-free hierarchical layout.
 */
(function() {
  class LayoutEngine {
    constructor() {
      this.orientation = 'TB'; // 'LR' (Left-to-Right) or 'TB' (Top-to-Bottom)
      
      // Node dimensions configuration
      this.dimensions = {
        root: { width: 250, height: 60, rx: 12 },
        module: { width: 300, height: 64, rx: 12 },
        submodule: { width: 260, height: 50, rx: 10 },
        tableWidth: 320,
        tableCollapsedHeight: 52,
        tableExpandedHeader: 48,
        tableSchemaHeader: 28,
        tableAttrRowHeight: 28,
        tableFooterHeight: 36
      };

      // Spacing configuration for LR orientation
      this.spacingLR = {
        levelGap: 160,       // Horizontal distance between levels
        siblingGap: 24,      // Vertical gap between siblings
        moduleGap: 48,       // Extra vertical separation between major modules
        submoduleGap: 30,    // Extra vertical separation between submodules
        tableGap: 36         // Vertical gap between tables
      };

      // Spacing configuration for TB orientation
      this.spacingTB = {
        levelGap: 160,
        siblingGap: 40,
        moduleGap: 80,
        submoduleGap: 80,
        tableGap: 90
      };
    }

    setOrientation(orientation) {
      this.orientation = orientation === 'TB' ? 'TB' : 'LR';
    }

    getNodeDimensions(node, isExpanded) {
      if (node.type === 'table') {
        const tWidth = this.dimensions.tableWidth;
        if (isExpanded) {
          const schema = window.STAR_APP_SCHEMA;
          const tData = (schema && schema.tables && schema.tables[node.name]) || node.raw || {};
          const colCount = tData.columns ? tData.columns.length : 0;
          const tHeight = this.dimensions.tableExpandedHeader + 
                          this.dimensions.tableSchemaHeader + 
                          (colCount * this.dimensions.tableAttrRowHeight) + 
                          this.dimensions.tableFooterHeight + 20; // 20px padding ensures 100% visible rows without clipping
          return { width: tWidth, height: tHeight, rx: 10 };
        } else {
          return { width: tWidth, height: this.dimensions.tableCollapsedHeight, rx: 10 };
        }
      }

      const dim = this.dimensions[node.type] || { width: 220, height: 50, rx: 8 };
      return { ...dim };
    }

    /**
     * Compute layout for the tree
     * @param {Object} rootNode - Root of the mindmap tree
     * @param {Map<string, boolean>} expansionState - map of nodeId -> isExpanded
     * @returns {Object} { nodes: Array, edges: Array, bounds: Object }
     */
    computeLayout(rootNode, expansionState) {
      const positionedNodes = [];
      const hierarchicalEdges = [];

      // Phase 1: Build visible tree and calculate subtree bounding boxes
      const visibleTree = this._buildVisibleTree(rootNode, expansionState);

      // Phase 2: Compute relative vertical coordinates recursively
      this._computeSubtreeExtents(visibleTree);

      // Phase 3: Compute final absolute coordinates (X, Y)
      const startX = 80;
      const startY = 80;
      this._assignCoordinates(visibleTree, startX, startY, 0, positionedNodes, hierarchicalEdges);

      // Phase 4: Calculate overall layout bounds
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      positionedNodes.forEach(n => {
        if (n.x < minX) minX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.x + n.width > maxX) maxX = n.x + n.width;
        if (n.y + n.height > maxY) maxY = n.y + n.height;
      });

      if (positionedNodes.length === 0) {
        minX = minY = 0;
        maxX = maxY = 600;
      } else if (this.orientation === 'TB') {
        // Reserve clearance space below tables for relational channel routing (all 42 non-overlapping lanes)
        maxY += 950;
      }

      return {
        nodes: positionedNodes,
        edges: hierarchicalEdges,
        bounds: {
          minX, minY, maxX, maxY,
          width: Math.max(100, maxX - minX),
          height: Math.max(100, maxY - minY)
        }
      };
    }

    _buildVisibleTree(node, expansionState) {
      const isExpanded = expansionState.get(node.id) === true;
      const dim = this.getNodeDimensions(node, isExpanded);

      const treeNode = {
        id: node.id,
        raw: node.raw || node,
        type: node.type,
        name: node.name,
        color: node.color,
        badge: node.badge,
        width: dim.width,
        height: dim.height,
        rx: dim.rx,
        isExpanded: isExpanded,
        hasChildren: Boolean(node.children && node.children.length > 0),
        childrenCount: node.children ? node.children.length : 0,
        visibleChildren: []
      };

      if (node.type !== 'table' && isExpanded && node.children && node.children.length > 0) {
        treeNode.visibleChildren = node.children.map(child => this._buildVisibleTree(child, expansionState));
      }

      return treeNode;
    }

    _computeSubtreeExtents(node) {
      const sp = this.orientation === 'LR' ? this.spacingLR : this.spacingTB;
      
      if (!node.visibleChildren || node.visibleChildren.length === 0) {
        node.extent = this.orientation === 'LR' ? node.height : node.width;
        return;
      }

      let totalExtent = 0;
      for (let i = 0; i < node.visibleChildren.length; i++) {
        const child = node.visibleChildren[i];
        this._computeSubtreeExtents(child);

        let gap = sp.siblingGap;
        if (child.type === 'table') gap = sp.tableGap;
        else if (child.type === 'submodule') gap = sp.submoduleGap;
        else if (child.type === 'module') gap = sp.moduleGap;

        totalExtent += child.extent;
        if (i < node.visibleChildren.length - 1) {
          totalExtent += gap;
        }
      }

      const ownSize = this.orientation === 'LR' ? node.height : node.width;
      node.extent = Math.max(ownSize, totalExtent);
    }

    _assignCoordinates(node, x, y, depth, nodesList, edgesList) {
      const sp = this.orientation === 'LR' ? this.spacingLR : this.spacingTB;

      if (this.orientation === 'LR') {
        node.x = x;
        node.y = y + (node.extent - node.height) / 2;
      } else {
        node.y = y;
        node.x = x + (node.extent - node.width) / 2;
      }

      nodesList.push(node);

      if (node.visibleChildren && node.visibleChildren.length > 0) {
        let currentOffset = this.orientation === 'LR' ? y : x;

        for (let i = 0; i < node.visibleChildren.length; i++) {
          const child = node.visibleChildren[i];
          let childGap = sp.siblingGap;
          if (child.type === 'table') childGap = sp.tableGap;
          else if (child.type === 'submodule') childGap = sp.submoduleGap;
          else if (child.type === 'module') childGap = sp.moduleGap;

          if (this.orientation === 'LR') {
            const nextX = node.x + node.width + sp.levelGap;
            const nextY = currentOffset;
            this._assignCoordinates(child, nextX, nextY, depth + 1, nodesList, edgesList);
            currentOffset += child.extent + childGap;

            // Connector: right of parent -> left of child header
            const parentY = node.type === 'table' && node.isExpanded ? node.y + 24 : node.y + node.height / 2;
            const childY = child.type === 'table' && child.isExpanded ? child.y + 24 : child.y + child.height / 2;

            edgesList.push({
              id: `edge_${node.id}_${child.id}`,
              sourceId: node.id,
              targetId: child.id,
              color: child.color || node.color || '#3B82F6',
              x1: node.x + node.width,
              y1: parentY,
              x2: child.x,
              y2: childY,
              type: 'hierarchical'
            });
          } else {
            const nextX = currentOffset;
            const nextY = node.y + node.height + sp.levelGap;
            this._assignCoordinates(child, nextX, nextY, depth + 1, nodesList, edgesList);
            currentOffset += child.extent + childGap;

            // Connector: bottom of parent -> top of child
            edgesList.push({
              id: `edge_${node.id}_${child.id}`,
              sourceId: node.id,
              targetId: child.id,
              color: child.color || node.color || '#3B82F6',
              x1: node.x + node.width / 2,
              y1: node.y + node.height,
              x2: child.x + child.width / 2,
              y2: child.y,
              type: 'hierarchical'
            });
          }
        }
      }
    }
  }

  window.STAR_APP_LAYOUT_ENGINE = LayoutEngine;
})();
