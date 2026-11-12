import ELK from "elkjs/lib/elk.bundled.js";
import type { SkillEdgeView, SkillNodeView } from "./viewTypes";

/** Demande supposée d'une compétence tant que le marché n'a pas été analysé (phase 8). */
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

/** Taille d'un nœud : (1 + demande) fois la taille de base, la demande étant bornée à [0 ; 1]. */
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
 * Place les compétences de gauche à droite, du prérequis vers ce qui en dépend (elkjs `layered`).
 * Les liens vers une compétence inconnue et les boucles sur soi-même sont ignorés.
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
