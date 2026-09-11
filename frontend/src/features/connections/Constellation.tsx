import { useMemo, useRef, useState } from "react";
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
} from "d3-force";
import { Plus, Minus, RotateCcw } from "lucide-react";
import type { GraphData, GraphNode } from "../../types";

export function Constellation({
  graph,
  onSelect,
}: {
  graph: GraphData;
  onSelect: (node: GraphNode) => void;
}) {
  const [scale, setScale] = useState(1),
    [pan, setPan] = useState({ x: 0, y: 0 }),
    [hover, setHover] = useState<string | null>(null);
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(
    null,
  );
  const layout = useMemo(() => {
    const nodes = graph.nodes.map((n, i) => ({
      ...n,
      x: 400 + Math.cos(i * 2.399) * Math.sqrt(i + 1) * 37,
      y: 270 + Math.sin(i * 2.399) * Math.sqrt(i + 1) * 37,
    }));
    const links = graph.edges.map((e) => ({ ...e }));
    const sim = forceSimulation(nodes)
      .force(
        "link",
        forceLink(links)
          .id((d: any) => d.id)
          .distance(108),
      )
      .force("charge", forceManyBody().strength(-210))
      .force("center", forceCenter(400, 265))
      .force("collide", forceCollide(34))
      .stop();
    for (let i = 0; i < 180; i++) sim.tick();
    return { nodes, links };
  }, [graph]);
  return (
    <div className="constellation-canvas">
      <svg
        viewBox="0 0 800 540"
        role="img"
        aria-label="Dream constellation"
        onPointerDown={(e) => {
          drag.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y };
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => {
          if (drag.current) {
            const bounds = e.currentTarget.getBoundingClientRect();
            const unitScale = Math.min(bounds.width / 800, bounds.height / 540);
            setPan({
              x: drag.current.px + (e.clientX - drag.current.x) / unitScale,
              y: drag.current.py + (e.clientY - drag.current.y) / unitScale,
            });
          }
        }}
        onPointerUp={() => (drag.current = null)}
        onPointerCancel={() => (drag.current = null)}
      >
        <defs>
          <radialGradient id="node-glow">
            <stop stopColor="#e7cba4" stopOpacity=".25" />
            <stop offset="1" stopColor="#e7cba4" stopOpacity="0" />
          </radialGradient>
        </defs>
        <g className="star-field" aria-hidden="true">
          {Array.from({ length: 65 }, (_, i) => (
            <circle
              key={i}
              cx={(i * 137.5) % 800}
              cy={(i * 83.9) % 540}
              r={i % 6 === 0 ? 1 : 0.5}
              fill="#cbbca7"
              opacity={0.1 + (i % 4) * 0.07}
            />
          ))}
        </g>
        <g
          transform={`translate(${pan.x} ${pan.y}) translate(400 270) scale(${scale}) translate(-400 -270)`}
        >
          {layout.links.map((edge: any) => (
            <line
              key={edge.id}
              x1={edge.source.x}
              y1={edge.source.y}
              x2={edge.target.x}
              y2={edge.target.y}
              stroke={
                hover && (edge.source.id === hover || edge.target.id === hover)
                  ? "#d7ba90"
                  : "#655c54"
              }
              strokeWidth={1}
              opacity={hover ? 0.8 : 0.6}
              strokeDasharray={edge.kind === "inferred" ? "4 5" : undefined}
            />
          ))}
          {layout.nodes.map((node) => (
            <g
              key={node.id}
              transform={`translate(${node.x} ${node.y})`}
              className={`graph-node ${node.kind}`}
              role="button"
              tabIndex={0}
              aria-label={node.label}
              onPointerDown={(e) => e.stopPropagation()}
              onClick={() => onSelect(node)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(node);
                }
              }}
              onMouseEnter={() => setHover(node.id)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(node.id)}
              onBlur={() => setHover(null)}
            >
              <title>{node.label}</title>
              {node.kind === "theme" && (
                <circle r={42} fill="url(#node-glow)" />
              )}
              <circle
                className="node-halo"
                r={node.kind === "dream" ? 11 : 18}
                fill="none"
                stroke="currentColor"
                strokeOpacity=".18"
              />
              <circle r={node.kind === "dream" ? 4 : 7} fill="currentColor" />
              <text
                y={node.kind === "dream" ? 25 : 33}
                textAnchor="middle"
                fill="currentColor"
                fontSize={node.kind === "dream" ? 10 : 12}
              >
                {node.kind === "dream"
                  ? node.date || node.label.slice(0, 20)
                  : node.label.slice(0, 35)}
              </text>
              {hover === node.id && node.kind === "dream" && (
                <text y={42} textAnchor="middle" fill="currentColor" fontSize={11}>
                  {node.label.length > 45 ? node.label.slice(0, 45) + "…" : node.label}
                </text>
              )}
            </g>
          ))}
        </g>
      </svg>
      <div className="map-tools">
        <button
          aria-label="Zoom in"
          onClick={() => setScale((s) => Math.min(2.5, s + 0.2))}
        >
          <Plus size={16} />
        </button>
        <button
          aria-label="Zoom out"
          onClick={() => setScale((s) => Math.max(0.4, s - 0.2))}
        >
          <Minus size={16} />
        </button>
        <button
          aria-label="Reset view"
          onClick={() => {
            setScale(1);
            setPan({ x: 0, y: 0 });
          }}
        >
          <RotateCcw size={15} />
        </button>
      </div>
      <div className="map-caption">
        <span>✦</span> DRAG TO EXPLORE · SELECT A THREAD
      </div>
    </div>
  );
}
