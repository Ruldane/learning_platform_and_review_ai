import type { SkillEdgeView, SkillNodeView } from "./viewTypes";

/** Assumed demand for a skill until the market has been analyzed (phase 8). */
export const DEFAULT_DEMAND = 0.5;
const BASE_WIDTH = 132;
const BASE_HEIGHT = 44;

export interface NodeSize {
  width: number;
  height: number;
}

export interface PositionedNode extends NodeSize {
  id: string;
  x: number;
  y: number;
}

export interface Positioned {
  nodes: PositionedNode[];
}

/** Node size: (1 + demand) times the base size, demand being bounded to [0; 1]. */
export function nodeSize(demand: number | null): NodeSize {
  const value = demand === null || Number.isNaN(demand) ? DEFAULT_DEMAND : demand;
  const scale = 1 + Math.min(Math.max(value, 0), 1);
  return { width: Math.round(BASE_WIDTH * scale), height: Math.round(BASE_HEIGHT * scale) };
}

const LAYOUT_OPTIONS = {
  "elk.algorithm": "layered",
  "elk.direction": "RIGHT",
  "elk.spacing.nodeNode": "28",
  "elk.layered.spacing.nodeNodeBetweenLayers": "72",
};

/**
 * Places the skills from left to right, from prerequisite to what depends on it (elkjs `layered`).
 * Links to an unknown skill and self-loops are ignored. elkjs (heavy)
 * is loaded only here, on the first layout: it stays out of the main bundle.
 */
export async function layoutGraph(
  nodes: SkillNodeView[],
  edges: SkillEdgeView[],
): Promise<Positioned> {
  if (nodes.length === 0) return { nodes: [] };
  const known = new Set(nodes.map((node) => node.id));
  const links = edges.filter(
    (edge) => edge.beforeId !== edge.afterId && known.has(edge.beforeId) && known.has(edge.afterId),
  );
  const { default: ELK } = await import("elkjs/lib/elk.bundled.js");
  const result = await new ELK().layout({
    id: "root",
    layoutOptions: LAYOUT_OPTIONS,
    children: nodes.map((node) => ({ id: node.id, ...nodeSize(node.demand) })),
    edges: links.map((edge, index) => ({
      id: `e${index}`,
      sources: [edge.beforeId],
      targets: [edge.afterId],
    })),
  });
  return {
    nodes: (result.children ?? []).map((child) => ({
      id: child.id,
      x: child.x ?? 0,
      y: child.y ?? 0,
      width: child.width ?? 0,
      height: child.height ?? 0,
    })),
  };
}
