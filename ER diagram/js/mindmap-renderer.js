/**
 * STAR APP DATABASE MIND MAP — MINDMAP RENDERER (ENHANCED)
 * Renders in-card structured table attributes, non-overlapping relational spline lanes,
 * and high-contrast cardinality badges.
 */
(function() {
  class MindmapRenderer {
    constructor(canvasEl, svgEl, nodesContainerEl) {
      this.canvasEl = canvasEl;
      this.svgEl = svgEl;
      this.nodesContainerEl = nodesContainerEl;

      // Event handlers
      this.onToggleExpand = null;
      this.onSelectNode = null;
      this.onNavigateFK = null;
      this.onHoverNode = null;
      this.onOpenDrawer = null;

      // Active state
      this.activeNodeId = null;
      this.hoveredTable = null;
      this.selectedTable = null;
      this.relMode = 'all'; // 'all', 'selected', 'none'
      this.orientation = 'TB'; // 'TB' or 'LR'

      // Node lookup map: nodeId -> positionedNode
      this.nodeMap = new Map();
      this.tableNodeMap = new Map(); // tableName -> positionedNode

      this._setupSvgDefs();
    }

    _setupSvgDefs() {
      this.svgEl.innerHTML = `
        <defs>
          <filter id="glow-filter" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <!-- Forward / Standard Arrow (pointing in path direction) -->
          <marker id="rel-arrow-forward" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#10B981" />
          </marker>
          <!-- Downward Arrow (pointing in path direction) -->
          <marker id="rel-arrow-down" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#10B981" />
          </marker>
          <!-- Amber marker for inactive/all relationships -->
          <marker id="rel-arrow-amber" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#F59E0B" />
          </marker>
        </defs>
        <g id="hierarchical-edges-group"></g>
        <g id="relational-lines-group"></g>
        <g id="relational-badges-group"></g>
      `;
    }

    render(layoutResult, options = {}) {
      const { nodes, edges, bounds } = layoutResult;
      if (options.relMode !== undefined) this.relMode = options.relMode;
      if (options.selectedTable !== undefined) this.selectedTable = options.selectedTable;
      if (options.hoveredTable !== undefined) this.hoveredTable = options.hoveredTable;
      if (options.orientation !== undefined) this.orientation = options.orientation;

      this.nodeMap.clear();
      this.tableNodeMap.clear();

      nodes.forEach(n => {
        this.nodeMap.set(n.id, n);
        if (n.type === 'table') {
          this.tableNodeMap.set(n.name, n);
        }
      });

      // 1. Render Hierarchical SVG connectors
      this._renderHierarchicalEdges(edges);

      // 2. Render Relational SVG connectors (foreign keys)
      this._renderRelationalEdges();

      // 3. Render HTML DOM Nodes
      this._renderNodes(nodes);
    }

    _renderHierarchicalEdges(edges) {
      const group = this.svgEl.querySelector('#hierarchical-edges-group');
      if (!group) return;

      const isTB = this.orientation === 'TB';
      let html = '';
      edges.forEach(e => {
        let pathData;
        if (isTB) {
          // In Top-to-Bottom mode: leave bottom of parent vertically, enter top of child vertically
          const dy = Math.max(24, Math.abs(e.y2 - e.y1) * 0.5);
          const cx1 = e.x1;
          const cy1 = e.y1 + dy;
          const cx2 = e.x2;
          const cy2 = e.y2 - dy;
          pathData = `M ${e.x1} ${e.y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${e.x2} ${e.y2}`;
        } else {
          // In Left-to-Right mode: leave right of parent horizontally, enter left of child horizontally
          const dx = Math.abs(e.x2 - e.x1) * 0.55;
          const cx1 = e.x1 + dx;
          const cy1 = e.y1;
          const cx2 = e.x2 - dx;
          const cy2 = e.y2;
          pathData = `M ${e.x1} ${e.y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${e.x2} ${e.y2}`;
        }

        html += `
          <path d="${pathData}" 
                class="hierarchical-edge" 
                stroke="${e.color || '#3B82F6'}" 
                data-edge-id="${e.id}" />
        `;
      });

      group.innerHTML = html;
    }

    _renderRelationalEdges() {
      const linesGroup = this.svgEl.querySelector('#relational-lines-group');
      const badgesGroup = this.svgEl.querySelector('#relational-badges-group');
      if (!linesGroup || !badgesGroup) return;

      if (this.relMode === 'none') {
        linesGroup.innerHTML = '';
        badgesGroup.innerHTML = '';
        return;
      }

      const allRels = window.STAR_APP_RELATIONSHIPS || [];

      // Filter visible relationships
      const visibleRels = allRels.filter(rel => {
        return this.tableNodeMap.has(rel.source) && this.tableNodeMap.has(rel.target);
      });

      // =========================================================================
      // STEP 1: RESOLVE COLUMNS & ROW Y POSITIONS FOR ALL VISIBLE RELATIONS
      // =========================================================================
      const relData = visibleRels.map(rel => {
        const sourceNode = this.tableNodeMap.get(rel.source);
        const targetNode = this.tableNodeMap.get(rel.target);
        const { srcColName, tgtColName } = this._resolveRelationColumns(rel);

        const sourceIsLeft = sourceNode.x < targetNode.x;
        const sourceSide = sourceIsLeft ? 'R' : 'L';
        const targetSide = sourceIsLeft ? 'L' : 'R';

        // Check if there is any intermediate table between source and target
        const minX = Math.min(sourceNode.x, targetNode.x);
        const maxX = Math.max(sourceNode.x, targetNode.x);
        let hasIntermediateTableTB = false;
        this.tableNodeMap.forEach((otherNode, name) => {
          if (name === rel.source || name === rel.target) return;
          if (otherNode.x > minX + 25 && otherNode.x < maxX - 25) {
            hasIntermediateTableTB = true;
          }
        });

        const isDirectlyConnected = (this.selectedTable && (this.selectedTable === rel.source || this.selectedTable === rel.target)) ||
                                    (this.hoveredTable && (this.hoveredTable === rel.source || this.hoveredTable === rel.target));
        const isHighlighted = isDirectlyConnected;

        return {
          rel,
          sourceNode,
          targetNode,
          srcColName,
          tgtColName,
          sourceIsLeft,
          sourceSide,
          targetSide,
          hasIntermediateTableTB,
          isHighlighted
        };
      });

      // Filter based on relMode:
      // If relMode === 'selected', only keep rels where either source or target is selected/hovered
      const activeRels = this.relMode === 'selected'
        ? relData.filter(d => d.isHighlighted)
        : relData;

      // =========================================================================
      // STEP 2: PRE-CALCULATE MULTI-PORT SLOTS ON SAME COLUMN ROW
      // When multiple arrows connect to the same column, distribute them side-by-side
      // =========================================================================
      const portUsage = new Map(); // key -> total count
      activeRels.forEach(d => {
        const sKey = `${d.rel.source}_${d.sourceSide}_${d.srcColName}`;
        const tKey = `${d.rel.target}_${d.targetSide}_${d.tgtColName}`;
        portUsage.set(sKey, (portUsage.get(sKey) || 0) + 1);
        portUsage.set(tKey, (portUsage.get(tKey) || 0) + 1);
      });

      const portSlots = new Map();
      activeRels.forEach(d => {
        const sKey = `${d.rel.source}_${d.sourceSide}_${d.srcColName}`;
        const tKey = `${d.rel.target}_${d.targetSide}_${d.tgtColName}`;
        const sTotal = portUsage.get(sKey) || 1;
        const sSlot = portSlots.get(sKey) || 0;
        portSlots.set(sKey, sSlot + 1);

        const tTotal = portUsage.get(tKey) || 1;
        const tSlot = portSlots.get(tKey) || 0;
        portSlots.set(tKey, tSlot + 1);

        // Distribute offsets vertically across row height: e.g. -10, -5, 0, 5, 10
        d.sOffset = sTotal > 1 ? (sSlot - (sTotal - 1) / 2) * 5.0 : 0;
        d.tOffset = tTotal > 1 ? (tSlot - (tTotal - 1) / 2) * 5.0 : 0;

        d.baseSrcY = d.sourceNode.isExpanded
          ? this._getColumnRowY(d.rel.source, d.srcColName, d.sourceNode)
          : d.sourceNode.y + d.sourceNode.height / 2;
        d.baseTgtY = d.targetNode.isExpanded
          ? this._getColumnRowY(d.rel.target, d.tgtColName, d.targetNode)
          : d.targetNode.y + d.targetNode.height / 2;

        d.srcY = d.baseSrcY + d.sOffset;
        d.tgtY = d.baseTgtY + d.tOffset;
      });

      // =========================================================================
      // STEP 3: PLANAR CONCENTRIC TRACK ASSIGNMENT (NO GAP INTERSECTIONS)
      // Group non-adjacent departures and arrivals by table and sort by Y!
      // Highest row (top) takes outermost track, lowest row (bottom) takes innermost track.
      // =========================================================================
      const nonAdjacentBySource = new Map();
      const nonAdjacentByTarget = new Map();

      activeRels.forEach(d => {
        if (d.hasIntermediateTableTB) {
          const sGapKey = `${d.rel.source}_${d.sourceSide}`;
          const tGapKey = `${d.rel.target}_${d.targetSide}`;
          if (!nonAdjacentBySource.has(sGapKey)) nonAdjacentBySource.set(sGapKey, []);
          nonAdjacentBySource.get(sGapKey).push(d);

          if (!nonAdjacentByTarget.has(tGapKey)) nonAdjacentByTarget.set(tGapKey, []);
          nonAdjacentByTarget.get(tGapKey).push(d);
        }
      });

      // Sort departure drops: lowest Y (greatest Y number) gets innermost track (rank 0), highest Y gets outermost track
      nonAdjacentBySource.forEach(list => {
        list.sort((a, b) => b.srcY - a.srcY);
        list.forEach((item, rank) => {
          item.dropRank = rank;
        });
      });

      // Sort arrival rises: lowest Y (greatest Y number) gets innermost track (rank 0), highest Y gets outermost track
      nonAdjacentByTarget.forEach(list => {
        list.sort((a, b) => b.tgtY - a.tgtY);
        list.forEach((item, rank) => {
          item.riseRank = rank;
        });
      });

      // Find global maximum bottom Y of all tables for bottom clearance baseline
      let globalMaxBottomY = 0;
      this.tableNodeMap.forEach(n => {
        globalMaxBottomY = Math.max(globalMaxBottomY, n.y + n.height);
      });

      // Track multi-edge adjacent pairs so adjacent lines don't overlap in the gap
      const adjacentPairUsage = new Map();
      const adjacentPairSlots = new Map();
      activeRels.forEach(d => {
        if (!d.hasIntermediateTableTB) {
          const pairKey = `${d.rel.source}__${d.rel.target}`;
          adjacentPairUsage.set(pairKey, (adjacentPairUsage.get(pairKey) || 0) + 1);
        }
      });

      // =========================================================================
      // STEP 4: GENERATE SVG PATHS AND BADGES
      // =========================================================================
      let linesHtml = '';
      let badgesHtml = '';
      let nonAdjacentChannelIdx = 0;
      let lrVerticalLaneIndex = 0;
      let lrCrossLaneIndex = 0;

      activeRels.forEach(d => {
        const { rel, sourceNode, targetNode, sourceIsLeft, isHighlighted, srcY, tgtY } = d;
        let pathData = '';
        let badgeX = 0;
        let badgeY = 0;
        let markerId = isHighlighted ? 'url(#rel-arrow-forward)' : 'url(#rel-arrow-amber)';

        if (this.orientation === 'TB') {
          // -------------------------------------------------------------------
          // TOP-TO-BOTTOM (VERTICAL) ORIENTATION
          // -------------------------------------------------------------------
          if (!d.hasIntermediateTableTB) {
            // Direct connection between immediate horizontal neighbors
            const pairKey = `${rel.source}__${rel.target}`;
            const pairTotal = adjacentPairUsage.get(pairKey) || 1;
            const pairSlot = adjacentPairSlots.get(pairKey) || 0;
            adjacentPairSlots.set(pairKey, pairSlot + 1);

            const midOffset = pairTotal > 1 ? (pairSlot - (pairTotal - 1) / 2) * 12.0 : 0;
            const r = 6;

            if (sourceIsLeft) {
              const x1 = sourceNode.x + sourceNode.width;
              const y1 = srcY;
              const x2 = targetNode.x;
              const y2 = tgtY;

              // Compute clean midX avoiding any vertical drop or rise tracks in this gap
              const sDropList = nonAdjacentBySource.get(`${rel.source}_R`) || [];
              const tRiseList = nonAdjacentByTarget.get(`${rel.target}_L`) || [];

              let clearLeft = x1 + 12;
              let clearRight = x2 - 12;
              if (sDropList.length > 0) {
                const maxDrop = 24 + (sDropList.length - 1) * 10;
                clearLeft = Math.max(clearLeft, x1 + maxDrop + 12);
              }
              if (tRiseList.length > 0) {
                const maxRise = 24 + (tRiseList.length - 1) * 10;
                clearRight = Math.min(clearRight, x2 - maxRise - 12);
              }

              const midX = clearRight > clearLeft + 16
                ? (clearLeft + clearRight) / 2 + midOffset
                : (x1 + x2) / 2 + midOffset;

              if (Math.abs(y1 - y2) < 2) {
                // Pure straight horizontal line
                pathData = `M ${x1} ${y1} H ${x2}`;
              } else {
                // Orthogonal routing with rounded corners and guaranteed straight entry
                const dy = y2 > y1 ? 1 : -1;
                pathData = `M ${x1} ${y1} ` +
                           `H ${midX - r} Q ${midX} ${y1} ${midX} ${y1 + dy * r} ` +
                           `V ${y2 - dy * r} Q ${midX} ${y2} ${midX + r} ${y2} ` +
                           `H ${x2}`;
              }
              badgeX = midX;
              badgeY = (y1 + y2) / 2;
            } else if (targetNode.x < sourceNode.x) {
              const x1 = sourceNode.x;
              const y1 = srcY;
              const x2 = targetNode.x + targetNode.width;
              const y2 = tgtY;
              const midX = (x1 + x2) / 2 + midOffset;

              if (Math.abs(y1 - y2) < 2) {
                pathData = `M ${x1} ${y1} H ${x2}`;
              } else {
                const dy = y2 > y1 ? 1 : -1;
                pathData = `M ${x1} ${y1} ` +
                           `H ${midX + r} Q ${midX} ${y1} ${midX} ${y1 + dy * r} ` +
                           `V ${y2 - dy * r} Q ${midX} ${y2} ${midX - r} ${y2} ` +
                           `H ${x2}`;
              }
              badgeX = midX;
              badgeY = (y1 + y2) / 2;
            } else {
              const startX = sourceNode.x + sourceNode.width * 0.5 + d.sOffset;
              const startY = srcY;
              const endX = targetNode.x + targetNode.width * 0.5 + d.tOffset;
              const endY = tgtY;
              pathData = `M ${startX} ${startY} L ${endX} ${endY}`;
              badgeX = (startX + endX) / 2;
              badgeY = (startY + endY) / 2;
              markerId = isHighlighted ? 'url(#rel-arrow-down)' : 'url(#rel-arrow-amber)';
            }
          } else {
            // Non-adjacent tables: Planar Concentric Clearance Channel Routing!
            // dropRank: 0 is lowest row (innermost drop track), higher rank is higher row (outermost drop track)
            // riseRank: 0 is lowest row (innermost rise track), higher rank is higher row (outermost rise track)
            const dropTrackOffset = 24 + (d.dropRank || 0) * 10;
            const riseTrackOffset = 24 + (d.riseRank || 0) * 10;

            // Dedicated unique clearance channel depth for EVERY non-adjacent relation
            const channelY = globalMaxBottomY + 36 + (nonAdjacentChannelIdx * 20);
            nonAdjacentChannelIdx++;

            const r = 6; // smooth corner radius

            if (sourceIsLeft) {
              const x1 = sourceNode.x + sourceNode.width;
              const y1 = srcY;
              const dropX = sourceNode.x + sourceNode.width + dropTrackOffset;
              const x2 = targetNode.x;
              const y2 = tgtY;
              const riseX = targetNode.x - riseTrackOffset;

              pathData = `M ${x1} ${y1} ` +
                         `H ${dropX - r} Q ${dropX} ${y1} ${dropX} ${y1 + r} ` +
                         `V ${channelY - r} Q ${dropX} ${channelY} ${dropX + r} ${channelY} ` +
                         `H ${riseX - r} Q ${riseX} ${channelY} ${riseX} ${channelY - r} ` +
                         `V ${y2 + r} Q ${riseX} ${y2} ${riseX + r} ${y2} ` +
                         `H ${x2}`;
              badgeX = (dropX + riseX) / 2;
              badgeY = channelY;
            } else {
              const x1 = sourceNode.x;
              const y1 = srcY;
              const dropX = sourceNode.x - dropTrackOffset;
              const x2 = targetNode.x + targetNode.width;
              const y2 = tgtY;
              const riseX = targetNode.x + targetNode.width + riseTrackOffset;

              pathData = `M ${x1} ${y1} ` +
                         `H ${dropX + r} Q ${dropX} ${y1} ${dropX} ${y1 + r} ` +
                         `V ${channelY - r} Q ${dropX} ${channelY} ${dropX - r} ${channelY} ` +
                         `H ${riseX + r} Q ${riseX} ${channelY} ${riseX} ${channelY - r} ` +
                         `V ${y2 + r} Q ${riseX} ${y2} ${riseX - r} ${y2} ` +
                         `H ${x2}`;
              badgeX = (dropX + riseX) / 2;
              badgeY = channelY;
            }
          }

        } else {
          // -------------------------------------------------------------------
          // LEFT-TO-RIGHT (HORIZONTAL) ORIENTATION
          // -------------------------------------------------------------------
          const dx = targetNode.x - sourceNode.x;
          const isSameColumn = Math.abs(dx) < 60;

          if (isSameColumn) {
            const minY = Math.min(sourceNode.y, targetNode.y) + 5;
            const maxY = Math.max(sourceNode.y + sourceNode.height, targetNode.y + targetNode.height) - 5;

            let hasIntermediateTable = false;
            this.tableNodeMap.forEach((otherNode, name) => {
              if (name === rel.source || name === rel.target) return;
              if (Math.abs(otherNode.x - sourceNode.x) < 60) {
                if (otherNode.y > minY && otherNode.y < maxY) {
                  hasIntermediateTable = true;
                }
              }
            });

            if (!hasIntermediateTable) {
              const rightEdge = Math.max(sourceNode.x + sourceNode.width, targetNode.x + targetNode.width);
              const channelX = rightEdge + 24;
              const y1 = srcY;
              const y2 = tgtY;
              const x1 = sourceNode.x + sourceNode.width;
              const x2 = targetNode.x + targetNode.width;
              const r = 6;
              const dir = y2 > y1 ? 1 : -1;

              pathData = `M ${x1} ${y1} ` +
                         `H ${channelX - r} Q ${channelX} ${y1} ${channelX} ${y1 + dir * r} ` +
                         `V ${y2 - dir * r} Q ${channelX} ${y2} ${channelX - r} ${y2} ` +
                         `H ${x2}`;
              badgeX = channelX;
              badgeY = (y1 + y2) / 2;
            } else {
              const lane = lrVerticalLaneIndex;
              lrVerticalLaneIndex++;

              const rightEdge = Math.max(sourceNode.x + sourceNode.width, targetNode.x + targetNode.width);
              const channelX = rightEdge + 36 + (lane * 20);

              const y1 = srcY;
              const y2 = tgtY;
              const x1 = sourceNode.x + sourceNode.width;
              const x2 = targetNode.x + targetNode.width;

              const r = 6;
              const dir = y2 > y1 ? 1 : -1;
              pathData = `M ${x1} ${y1} ` +
                         `H ${channelX - r} Q ${channelX} ${y1} ${channelX} ${y1 + dir * r} ` +
                         `V ${y2 - dir * r} Q ${channelX} ${y2} ${channelX - r} ${y2} ` +
                         `H ${x2}`;
              badgeX = channelX;
              badgeY = (y1 + y2) / 2;
            }

          } else if (targetNode.x > sourceNode.x + 60) {
            const lane = lrCrossLaneIndex;
            lrCrossLaneIndex++;

            const x1 = sourceNode.x + sourceNode.width;
            const y1 = srcY;
            const x2 = targetNode.x;
            const y2 = tgtY;

            const dx = Math.max(70, Math.abs(x2 - x1) * 0.45);
            const dyLane = (lane % 5 - 2) * 12;

            pathData = `M ${x1} ${y1} C ${x1 + dx} ${y1 + dyLane}, ${x2 - dx} ${y2 + dyLane}, ${x2} ${y2}`;
            badgeX = (x1 + x2) / 2;
            badgeY = (y1 + y2) / 2 + dyLane;

          } else {
            const lane = lrCrossLaneIndex;
            lrCrossLaneIndex++;

            const x1 = sourceNode.x;
            const y1 = srcY;
            const x2 = targetNode.x + targetNode.width;
            const y2 = tgtY;

            const dx = Math.max(70, Math.abs(x1 - x2) * 0.45);
            const dyLane = (lane % 5 - 2) * 12;

            pathData = `M ${x1} ${y1} C ${x1 - dx} ${y1 + dyLane}, ${x2 + dx} ${y2 + dyLane}, ${x2} ${y2}`;
            badgeX = (x1 + x2) / 2;
            badgeY = (y1 + y2) / 2 + dyLane;
          }
        }

        const strokeColor = isHighlighted ? '#10B981' : 'rgba(245, 158, 11, 0.65)';
        const strokeWidth = isHighlighted ? 2.6 : 1.8;
        const strokeDash = isHighlighted ? 'none' : '5,4';

        linesHtml += `
          <g class="relational-edge-group ${isHighlighted ? 'active-rel' : ''}" data-rel-id="${rel.id}" data-source="${rel.source}" data-target="${rel.target}">
            <path d="${pathData}" class="rel-hitbox" stroke="transparent" stroke-width="14" fill="none" />
            <path d="${pathData}" 
                  class="relational-edge ${isHighlighted ? 'highlighted' : ''}" 
                  stroke="${strokeColor}" 
                  stroke-width="${strokeWidth}" 
                  stroke-dasharray="${strokeDash}"
                  marker-end="${markerId}" />
            <title>${rel.source} ➔ ${rel.target} (${rel.cardinality})\nFK: ${rel.foreign_key || 'id reference'}\n${rel.description}</title>
          </g>
        `;

        badgesHtml += `
          <g class="rel-badge-group ${isHighlighted ? 'active' : ''}" data-rel-id="${rel.id}" data-source="${rel.source}" data-target="${rel.target}" transform="translate(${badgeX}, ${badgeY})">
            <rect x="-16" y="-9" width="32" height="18" rx="5" class="rel-pill-rect ${isHighlighted ? 'active' : ''}" />
            <text x="0" y="0.5" class="rel-cardinality-text ${isHighlighted ? 'active' : ''}">${rel.cardinality}</text>
            <title>${rel.source} ➔ ${rel.target} (${rel.cardinality})\nFK: ${rel.foreign_key || 'id reference'}</title>
          </g>
        `;
      });

      linesGroup.innerHTML = linesHtml;
      badgesGroup.innerHTML = badgesHtml;

      // Add hover handlers to relational edge groups and badges
      const attachHover = (el) => {
        el.addEventListener('mouseenter', () => {
          const s = el.getAttribute('data-source');
          const t = el.getAttribute('data-target');
          this._highlightTablePair(s, t);
        });
        el.addEventListener('mouseleave', () => {
          this._clearTablePairHighlight();
        });
        el.addEventListener('click', (e) => {
          e.stopPropagation();
          const t = el.getAttribute('data-target');
          if (this.onSelectNode) {
            const targetPosNode = this.tableNodeMap.get(t);
            if (targetPosNode) this.onSelectNode(targetPosNode);
          }
        });
      };

      linesGroup.querySelectorAll('.relational-edge-group').forEach(attachHover);
      badgesGroup.querySelectorAll('.rel-badge-group').forEach(attachHover);
    }

    _resolveRelationColumns(rel) {
      const schema = window.STAR_APP_SCHEMA;
      const srcTable = schema && schema.tables && schema.tables[rel.source];
      const tgtTable = schema && schema.tables && schema.tables[rel.target];

      const srcCols = (srcTable && srcTable.columns) || [];
      const tgtCols = (tgtTable && tgtTable.columns) || [];

      // Target table (Child) has the foreign key column
      let tgtColName = rel.foreign_key;
      if (!tgtCols.some(c => c.name === tgtColName)) {
        const fk = tgtCols.find(c => c.is_fk);
        tgtColName = fk ? fk.name : (tgtCols[0] ? tgtCols[0].name : '');
      }

      // Source table (Parent) has the referenced column
      let srcColName = rel.foreign_key;
      if (!srcCols.some(c => c.name === srcColName)) {
        const pk = srcCols.find(c => c.is_pk);
        srcColName = pk ? pk.name : (srcCols[0] ? srcCols[0].name : '');
      }

      return { srcColName, tgtColName };
    }

    _getColumnRowY(tableName, columnName, tableNode) {
      const schema = window.STAR_APP_SCHEMA;
      const cols = (schema && schema.tables && schema.tables[tableName] && schema.tables[tableName].columns) || [];
      const idx = cols.findIndex(c => c.name === columnName);
      if (idx < 0) return tableNode.y + (tableNode.isExpanded ? 36 : 26);
      const HEADER = 48, SCHEMA_HDR = 28, ROW_H = 28;
      return tableNode.y + HEADER + SCHEMA_HDR + (idx * ROW_H) + (ROW_H / 2);
    }

    _getPKRowY(tableName, tableNode) {
      const schema = window.STAR_APP_SCHEMA;
      const cols = (schema && schema.tables && schema.tables[tableName] && schema.tables[tableName].columns) || [];
      const pkIdx = cols.findIndex(c => c.is_pk);
      if (pkIdx < 0) return tableNode.y + (tableNode.isExpanded ? 36 : 26);
      const HEADER = 48, SCHEMA_HDR = 28, ROW_H = 28;
      return tableNode.y + HEADER + SCHEMA_HDR + (pkIdx * ROW_H) + (ROW_H / 2);
    }

    _highlightTablePair(sourceName, targetName) {
      document.querySelectorAll('.node-table').forEach(el => {
        const title = el.getAttribute('data-table-name');
        if (title === sourceName || title === targetName) {
          el.classList.add('edge-hover-highlight');
        } else {
          el.classList.add('edge-dim');
        }
      });
    }

    _clearTablePairHighlight() {
      document.querySelectorAll('.node-table').forEach(el => {
        el.classList.remove('edge-hover-highlight', 'edge-dim');
      });
    }

    _renderNodes(nodes) {
      const container = this.nodesContainerEl;
      container.innerHTML = '';

      const fragment = document.createDocumentFragment();

      nodes.forEach(node => {
        const el = document.createElement('div');
        el.className = `mindmap-node node-${node.type} ${node.isExpanded ? 'is-expanded' : 'is-collapsed'}`;
        el.id = `node-${node.id}`;
        el.style.left = `${node.x}px`;
        el.style.top = `${node.y}px`;
        el.style.width = `${node.width}px`;
        el.style.height = `${node.height}px`;

        if (node.type === 'table') {
          el.setAttribute('data-table-name', node.name);
        }

        if (node.color) {
          el.style.setProperty('--node-accent', node.color);
        }

        // Inner HTML based on node type
        el.innerHTML = this._generateNodeContent(node);

        // Attach event listeners
        this._attachNodeEvents(el, node);

        fragment.appendChild(el);
      });

      container.appendChild(fragment);
    }

    _generateNodeContent(node) {
      const toggleBtn = `
        <button type="button" class="node-toggle-btn" title="${node.isExpanded ? 'Collapse' : 'Expand'}" data-action="toggle">
          ${node.isExpanded ? '−' : '+'}
        </button>
      `;

      switch (node.type) {
        case 'root':
          return `
            <div class="node-inner root-inner">
              <div class="node-icon root-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                  <ellipse cx="12" cy="5" rx="9" ry="3"/>
                  <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                  <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                </svg>
              </div>
              <div class="node-text">
                <div class="node-title">${node.name}</div>
                <div class="node-subtitle">29 Database Tables &bull; 8 Core Modules</div>
              </div>
              ${toggleBtn}
            </div>
          `;

        case 'module':
          const modNum = node.raw.num || '';
          return `
            <div class="node-inner module-inner">
              <span class="module-number-pill" style="background:${node.color}">${modNum}</span>
              <div class="node-text">
                <div class="node-title" title="${node.name}">${node.name}</div>
                <div class="node-meta">${node.childrenCount} Submodules</div>
              </div>
              ${toggleBtn}
            </div>
          `;

        case 'submodule':
          return `
            <div class="node-inner submodule-inner">
              <div class="submod-dot" style="background:${node.color}"></div>
              <div class="node-text">
                <div class="node-title" title="${node.name}">${node.name}</div>
                <div class="node-meta">${node.childrenCount} Tables</div>
              </div>
              ${toggleBtn}
            </div>
          `;

        case 'table':
          const isSelected = this.selectedTable === node.name;
          const isHovered = this.hoveredTable === node.name;
          const tableData = (window.STAR_APP_SCHEMA && window.STAR_APP_SCHEMA.tables && window.STAR_APP_SCHEMA.tables[node.name]) || {};
          const columns = tableData.columns || [];
          const colCount = columns.length;
          const pks = columns.filter(c => c.is_pk).length;
          const fks = columns.filter(c => c.is_fk).length;

          // If expanded, render complete structured in-card table schema!
          if (node.isExpanded) {
            const attrRowsHtml = columns.map(col => {
              let keyPill = '';
              if (col.is_pk) {
                keyPill = '<span class="attr-pill pk" title="Primary Key">PK</span>';
              } else if (col.is_fk) {
                keyPill = '<span class="attr-pill fk" title="Foreign Key">FK</span>';
              } else if (col.is_derived) {
                keyPill = '<span class="attr-pill derived" title="Calculated Derived Field">DERIVED</span>';
              } else {
                keyPill = '<span class="attr-bullet">&bull;</span>';
              }

              let fkTargetHtml = '';
              if (col.references) {
                const targetTable = col.references.split('.')[0];
                fkTargetHtml = `
                  <button type="button" class="attr-fk-target-pill" data-jump-table="${targetTable}" title="Jump to referenced table ${col.references}">
                    ➔ ${targetTable}
                  </button>
                `;
              }

              let uniqueHtml = col.is_unique ? '<span class="attr-pill unique" title="Unique Constraint">UK</span>' : '';

              return `
                <div class="card-attr-row ${col.is_pk ? 'row-pk' : (col.is_fk ? 'row-fk' : '')}">
                  <div class="attr-left">
                    ${keyPill}
                    <span class="attr-col-name" title="${col.name}">${col.name}</span>
                    ${uniqueHtml}
                  </div>
                  <div class="attr-right">
                    ${fkTargetHtml}
                  </div>
                </div>
              `;
            }).join('');

            return `
              <div class="node-inner table-inner expanded ${isSelected ? 'selected' : ''} ${isHovered ? 'hovered' : ''}">
                <!-- Card Header -->
                <div class="table-card-header" data-action="toggle">
                  <div class="table-header-left" data-action="toggle">
                    <div class="table-icon-wrap" style="color:${node.color}" data-action="toggle">
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                        <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/><path d="M9 3v18"/>
                      </svg>
                    </div>
                    <span class="table-title-expanded" title="Table: ${node.name}" data-action="toggle">${node.name}</span>
                    <span class="table-card-num-badge">#${tableData.table_number || ''}</span>
                  </div>
                  <div class="table-header-right">
                    ${toggleBtn}
                  </div>
                </div>

                <!-- Attributes Section -->
                <div class="table-card-body">
                  <div class="table-card-schema-heading">
                    <span>ATTRIBUTES (${colCount})</span>
                    <span class="schema-legend-hint">${pks} PK &bull; ${fks} FK</span>
                  </div>
                  <div class="table-card-rows">
                    ${attrRowsHtml}
                  </div>
                </div>

                <!-- Card Footer -->
                <div class="table-card-footer" data-action="open-drawer" title="Click to open full table schema details & relationships">
                  <span class="card-footer-submod" data-action="open-drawer">${tableData.module_info ? tableData.module_info.submodule_name : ''}</span>
                  <button type="button" class="btn-inspect-drawer" data-action="open-drawer" title="Open full details & relationships">
                    Details ➔
                  </button>
                </div>
              </div>
            `;
          }

          // Collapsed state: Compact horizontal summary pill
          return `
            <div class="node-inner table-inner collapsed ${isSelected ? 'selected' : ''} ${isHovered ? 'hovered' : ''}">
              <div class="table-collapsed-left" data-action="toggle">
                <div class="table-icon-wrap" style="color:${node.color}" data-action="toggle">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                    <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/><path d="M9 3v18"/>
                  </svg>
                </div>
                <div class="table-collapsed-info" data-action="toggle">
                  <div class="table-title-collapsed" title="Table: ${node.name}" data-action="toggle">${node.name}</div>
                  <div class="table-collapsed-badges">
                    <span class="badge-tag pk-tag" title="${pks} Primary Key(s)">PK</span>
                    ${fks > 0 ? `<span class="badge-tag fk-tag" title="${fks} Foreign Key(s)">FK</span>` : ''}
                    <span class="badge-col-count">${colCount} cols</span>
                  </div>
                </div>
              </div>
              <div class="table-collapsed-right">
                <span class="table-num-pill">#${tableData.table_number || ''}</span>
                <button type="button" class="btn-inspect-drawer btn-inspect-collapsed" data-action="open-drawer" title="Open full details & relationships">
                  Details ➔
                </button>
                ${toggleBtn}
              </div>
            </div>
          `;

        default:
          return `<div class="node-inner">${node.name} ${toggleBtn}</div>`;
      }
    }

    _attachNodeEvents(el, node) {
      // 1. Any toggle triggers (the + / - button, header, collapsed pill, table icon)
      el.querySelectorAll('[data-action="toggle"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          if (this.onToggleExpand) {
            this.onToggleExpand(node.id);
          }
        });
      });

      // 2. Foreign key jump links inside table card
      el.querySelectorAll('[data-jump-table]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const targetTable = btn.getAttribute('data-jump-table');
          if (this.onNavigateFK) {
            this.onNavigateFK(targetTable);
          }
        });
      });

      // 3. Details triggers in expanded card footer and collapsed header
      el.querySelectorAll('[data-action="open-drawer"]').forEach(drawerBtn => {
        drawerBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          e.preventDefault();
          if (this.onOpenDrawer) {
            this.onOpenDrawer(node.name);
          }
        });
      });

      // 4. Clicking table card body / row
      el.addEventListener('click', (e) => {
        if (e.target.closest('[data-action="toggle"]') || 
            e.target.closest('[data-jump-table]') || 
            e.target.closest('[data-action="open-drawer"]')) {
          return;
        }

        if (node.type === 'table') {
          // If in collapsed mode, clicking expands it and reveals details
          if (!node.isExpanded) {
            if (this.onToggleExpand) this.onToggleExpand(node.id);
            if (this.onOpenDrawer) this.onOpenDrawer(node.name);
          } else {
            // If already expanded, select it to focus relationships and open drawer
            if (this.onSelectNode) this.onSelectNode(node);
            if (this.onOpenDrawer) this.onOpenDrawer(node.name);
          }
        } else {
          if (this.onToggleExpand) {
            this.onToggleExpand(node.id);
          }
        }
      });

      // 5. Hover events for table nodes
      if (node.type === 'table') {
        el.addEventListener('mouseenter', () => {
          if (this.onHoverNode) this.onHoverNode(node.name);
        });
        el.addEventListener('mouseleave', () => {
          if (this.onHoverNode) this.onHoverNode(null);
        });
      }
    }
  }

  window.STAR_APP_RENDERER = MindmapRenderer;
})();
