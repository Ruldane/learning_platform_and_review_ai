import { useEffect, useRef, useState } from "react";
import { layoutGraph, type PositionedNode } from "../layoutGraph";
import type { SkillEdgeView, SkillNodeView } from "../viewTypes";

/** What changes the layout: the skills, their demand (size) and the links. Not the level. */
function structureKey(nodes: SkillNodeView[], edges: SkillEdgeView[]): string {
  return JSON.stringify([
    nodes.map((node) => [node.id, node.demand]),
    edges.map((edge) => [edge.beforeId, edge.afterId]),
  ]);
}

export interface GraphLayout {
  placed: Map<string, PositionedNode> | null;
  failed: boolean;
}

/**
 * Computes the layout (asynchronously) when the graph's structure changes: a reread that only
 * changes a level keeps the positions, with no recalculation or flicker.
 */
export function useGraphLayout(nodes: SkillNodeView[], edges: SkillEdgeView[]): GraphLayout {
  const [layout, setLayout] = useState<GraphLayout>({ placed: null, failed: false });
  const latest = useRef({ nodes, edges });
  const key = structureKey(nodes, edges);

  useEffect(() => {
    latest.current = { nodes, edges };
  });

  useEffect(() => {
    let cancelled = false;
    layoutGraph(latest.current.nodes, latest.current.edges).then(
      (result) => {
        if (cancelled) return;
        setLayout({ placed: new Map(result.nodes.map((node) => [node.id, node])), failed: false });
      },
      () => {
        if (!cancelled) setLayout({ placed: null, failed: true });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [key]);

  return layout;
}
