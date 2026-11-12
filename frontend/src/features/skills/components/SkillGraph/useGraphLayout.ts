import { useEffect, useRef, useState } from "react";
import { layoutGraph, type PositionedNode } from "../layoutGraph";
import type { SkillEdgeView, SkillNodeView } from "../viewTypes";

/** Ce qui change la mise en page : les compétences, leur demande (taille) et les liens. Pas le niveau. */
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
 * Calcule la mise en page (asynchrone) quand la structure du graphe change : une relecture qui ne
 * fait que changer un niveau garde les positions, sans recalcul ni clignotement.
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
