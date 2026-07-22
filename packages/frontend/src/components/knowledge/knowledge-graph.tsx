"use client"

import { useKnowledgeStore } from "@/lib/store/knowledge-store"
import { KNOWLEDGE_TYPE_COLORS, KNOWLEDGE_TYPE_LABELS } from "@/lib/types/knowledge"
import type { KnowledgeGraphNode, KnowledgeGraphEdge } from "@/lib/types/knowledge"

export default function KnowledgeGraph() {
  const { graphNodes, graphEdges, selectedItemId, selectItem } = useKnowledgeStore()

  const getNodeById = (id: string) => graphNodes.find((n) => n.id === id)

  const svgWidth = 680
  const svgHeight = 440

  return (
    <div className="w-full h-full bg-[var(--bg-surface)] rounded-xl border border-[var(--border-default)] overflow-hidden relative">
      <div className="absolute top-3 left-3 z-10">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2">Knowledge Graph</h3>
        <div className="flex flex-wrap gap-2">
          {Object.entries(KNOWLEDGE_TYPE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1.5 text-[10px] text-[var(--text-secondary)]">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
              {KNOWLEDGE_TYPE_LABELS[type as keyof typeof KNOWLEDGE_TYPE_LABELS]}
            </div>
          ))}
        </div>
      </div>

      <svg
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        className="w-full h-full"
        style={{ minHeight: 400 }}
      >
        <defs>
          <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="var(--text-tertiary)" />
          </marker>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="selectedGlow">
            <feGaussianBlur stdDeviation="5" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {graphEdges.map((edge) => {
          const sourceNode = getNodeById(edge.source)
          const targetNode = getNodeById(edge.target)
          if (!sourceNode || !targetNode) return null

          const isSelected =
            selectedItemId === edge.source || selectedItemId === edge.target
          const opacity = selectedItemId ? (isSelected ? 0.9 : 0.15) : 0.4

          const dx = targetNode.x - sourceNode.x
          const dy = targetNode.y - sourceNode.y
          const len = Math.sqrt(dx * dx + dy * dy)
          const offsetX = (dx / len) * (sourceNode.size + 4)
          const offsetY = (dy / len) * (sourceNode.size + 4)
          const targetOffsetX = (dx / len) * (targetNode.size + 8)
          const targetOffsetY = (dy / len) * (targetNode.size + 8)

          const midX = (sourceNode.x + targetNode.x) / 2
          const midY = (sourceNode.y + targetNode.y) / 2

          return (
            <g key={edge.id}>
              <line
                x1={sourceNode.x + offsetX}
                y1={sourceNode.y + offsetY}
                x2={targetNode.x - targetOffsetX}
                y2={targetNode.y - targetOffsetY}
                stroke="var(--text-tertiary)"
                strokeWidth={isSelected ? 2.5 : 1.5}
                strokeOpacity={opacity}
                markerEnd="url(#arrowhead)"
                className="transition-all duration-300"
              />
              {isSelected && (
                <text
                  x={midX}
                  y={midY - 6}
                  textAnchor="middle"
                  fill="var(--text-secondary)"
                  fontSize="9"
                  fontFamily="Inter, sans-serif"
                >
                  {edge.label}
                </text>
              )}
            </g>
          )
        })}

        {graphNodes.map((node) => {
          const isSelected = selectedItemId === node.id
          const isDimmed = selectedItemId && !isSelected
          const nodeOpacity = isDimmed ? 0.25 : 1

          return (
            <g
              key={node.id}
              onClick={() => selectItem(isSelected ? null : node.id)}
              className="cursor-pointer transition-all duration-300"
              style={{ opacity: nodeOpacity }}
            >
              <circle
                cx={node.x}
                cy={node.y}
                r={node.size}
                fill={node.color}
                fillOpacity={0.15}
                stroke={node.color}
                strokeWidth={isSelected ? 3 : 1.5}
                filter={isSelected ? "url(#selectedGlow)" : undefined}
                className="transition-all duration-300"
              />
              <circle
                cx={node.x}
                cy={node.y}
                r={node.size * 0.4}
                fill={node.color}
                className="transition-all duration-300"
              />
              <text
                x={node.x}
                y={node.y + node.size + 14}
                textAnchor="middle"
                fill={isSelected ? "var(--text-primary)" : "var(--text-secondary)"}
                fontSize="10"
                fontWeight={isSelected ? 600 : 400}
                fontFamily="Inter, sans-serif"
                className="transition-all duration-300"
              >
                {node.label}
              </text>
            </g>
          )
        })}
      </svg>

      {selectedItemId && (
        <button
          onClick={() => selectItem(null)}
          className="absolute top-3 right-3 px-3 py-1.5 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] bg-[var(--bg-hover)] hover:bg-[var(--bg-active)] rounded-lg transition-colors z-10"
        >
          Clear Selection
        </button>
      )}
    </div>
  )
}
