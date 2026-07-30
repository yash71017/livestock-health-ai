import React, { useState, useMemo } from 'react';
import { Box, Typography } from '@mui/material';
import {
  forceSimulation, forceLink, forceManyBody, forceCollide, forceX, forceY,
} from 'd3-force';

/**
 * ForceGraph — disease <-> symptom network.
 *
 * d3-force is used for the LAYOUT MATH ONLY. React renders the SVG.
 * This avoids the usual d3-vs-React conflict where both try to own the DOM.
 *
 * The simulation is run to completion synchronously (500 ticks on 45 nodes
 * takes a few milliseconds) rather than animated frame-by-frame. Deterministic,
 * no animation loop, no cleanup to get wrong.
 *
 * Force parameters were tuned by measuring the minimum pairwise distance
 * between labelled symptom nodes. The defaults produced 14 overlapping label
 * pairs; these values produce none, while still fitting the viewBox:
 *   - strong repulsion (-900) to open up the dense centre
 *   - extra collision padding on SYMPTOM nodes, since only they are always
 *     labelled and therefore need room for text
 *   - forceX/forceY instead of forceCenter: forceCenter only centres the mean
 *     and lets the layout sprawl past the canvas, which then gets clamped into
 *     a squashed mess at the edges
 */

const PINE = '#1F5244';
const PINE_LIGHT = '#3C7A68';
const OCHRE = '#C4893D';
const INK = '#1B241F';
const MUTED = '#5C6862';

const WIDTH = 900;
const HEIGHT = 640;

export default function ForceGraph({ data }) {
  const [hovered, setHovered] = useState(null);

  // Run the simulation once, whenever the data changes.
  const layout = useMemo(() => {
    if (!data?.nodes?.length) return null;

    // Clone: d3 mutates the objects it is given.
    const nodes = data.nodes.map((n) => ({ ...n }));
    const links = data.links.map((l) => ({ ...l }));

    const sim = forceSimulation(nodes)
      .force('link', forceLink(links).id((d) => d.id).distance(105).strength(0.3))
      .force('charge', forceManyBody().strength(-900))
      .force('x', forceX(WIDTH / 2).strength(0.13))
      .force('y', forceY(HEIGHT / 2).strength(0.26))
      // Symptoms get much more padding: they are always labelled, so they need
      // room for the text, not just the circle.
      .force('collide', forceCollide().radius(
        (d) => radius(d) + (d.type === 'symptom' ? 34 : 14)
      ))
      .stop();

    for (let i = 0; i < 500; i += 1) sim.tick();

    // Keep everything inside the viewport
    nodes.forEach((n) => {
      n.x = Math.max(40, Math.min(WIDTH - 40, n.x));
      n.y = Math.max(30, Math.min(HEIGHT - 30, n.y));
    });

    return { nodes, links };
  }, [data]);

  // Which nodes/links are connected to the hovered node
  const connected = useMemo(() => {
    if (!hovered || !layout) return null;
    const ids = new Set([hovered]);
    layout.links.forEach((l) => {
      const s = l.source.id ?? l.source;
      const t = l.target.id ?? l.target;
      if (s === hovered) ids.add(t);
      if (t === hovered) ids.add(s);
    });
    return ids;
  }, [hovered, layout]);

  if (!layout) return null;

  const hoveredNode = hovered
    ? layout.nodes.find((n) => n.id === hovered)
    : null;

  return (
    <Box>
      <Box
        component="svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        sx={{ width: '100%', height: 'auto', display: 'block', cursor: 'default' }}
        onMouseLeave={() => setHovered(null)}
      >
        {/* ── Links ── */}
        {layout.links.map((l, i) => {
          const s = l.source; const t = l.target;
          const sid = s.id ?? s; const tid = t.id ?? t;
          const active = !connected || (connected.has(sid) && connected.has(tid));
          return (
            <line
              key={i}
              x1={s.x} y1={s.y} x2={t.x} y2={t.y}
              stroke={active ? PINE_LIGHT : '#C9D2CC'}
              strokeOpacity={active ? Math.min(0.15 + l.weight * 0.06, 0.6) : 0.12}
              strokeWidth={active ? Math.min(0.8 + l.weight * 0.25, 3) : 0.6}
            />
          );
        })}

        {/* ── Nodes ── */}
        {layout.nodes.map((n) => {
          const active = !connected || connected.has(n.id);
          const isDisease = n.type === 'disease';
          return (
            <g
              key={n.id}
              transform={`translate(${n.x},${n.y})`}
              onMouseEnter={() => setHovered(n.id)}
              style={{ cursor: 'pointer' }}
            >
              <circle
                r={radius(n)}
                fill={isDisease ? PINE : OCHRE}
                fillOpacity={active ? 0.92 : 0.18}
                stroke="#fff"
                strokeWidth={1.5}
                strokeOpacity={active ? 1 : 0.3}
              />
              {/* Symptom labels always shown (only 15, and they are the hubs).
                  Disease labels only on hover — 30 would be unreadable. */}
              {(!isDisease || hovered === n.id) && (
                <text
                  y={radius(n) + 13}
                  textAnchor="middle"
                  style={{
                    fontSize: isDisease ? 11 : 11.5,
                    fontWeight: isDisease ? 700 : 600,
                    fill: active ? INK : '#A8B3AC',
                    pointerEvents: 'none',
                    // White outline painted behind the glyphs so labels stay
                    // readable where they cross links or other labels.
                    paintOrder: 'stroke',
                    stroke: '#fff',
                    strokeWidth: 3.5,
                    strokeLinejoin: 'round',
                  }}
                >
                  {n.label}
                </text>
              )}
            </g>
          );
        })}
      </Box>

      {/* ── Legend / readout ── */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, flexWrap: 'wrap', mt: 1 }}>
        <LegendDot color={PINE} label="Disease" />
        <LegendDot color={OCHRE} label="Symptom" />
        <Typography sx={{ fontSize: 12, color: MUTED }}>
          Circle size = number of connections · hover to isolate
        </Typography>
      </Box>

      {hoveredNode && (
        <Box sx={{ mt: 1.5, p: 1.5, borderRadius: '10px', backgroundColor: 'rgba(31,82,68,.05)' }}>
          <Typography sx={{ fontSize: 13.5, fontWeight: 700 }}>
            {hoveredNode.label}
          </Typography>
          <Typography sx={{ fontSize: 12.5, color: MUTED }}>
            {hoveredNode.type === 'disease'
              ? `Linked to ${hoveredNode.degree} symptom${hoveredNode.degree === 1 ? '' : 's'}`
              : `Appears in ${hoveredNode.degree} disease${hoveredNode.degree === 1 ? '' : 's'}`}
            {hoveredNode.type === 'symptom' && hoveredNode.degree > 15 &&
              ' — shared by most diseases, so a weak discriminator'}
            {hoveredNode.type === 'symptom' && hoveredNode.degree <= 3 &&
              ' — rare, so a strong clue'}
          </Typography>
        </Box>
      )}
    </Box>
  );
}

function radius(n) {
  const d = n.degree || 1;
  return n.type === 'disease'
    ? Math.max(5, Math.min(4 + d * 0.9, 13))
    : Math.max(7, Math.min(6 + d * 0.55, 20));
}

function LegendDot({ color, label }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
      <Box sx={{ width: 11, height: 11, borderRadius: '50%', backgroundColor: color }} />
      <Typography sx={{ fontSize: 12.5, color: MUTED }}>{label}</Typography>
    </Box>
  );
}