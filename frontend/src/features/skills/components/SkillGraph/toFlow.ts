import { MarkerType, type AriaLabelConfig, type Edge } from "@xyflow/react";
import { t } from "@/shared/i18n/t";
import type { PositionedNode } from "../layoutGraph";
import { levelKey } from "../levels";
import type { SkillEdgeView, SkillNodeView } from "../viewTypes";
import type { SkillFlowNode } from "./SkillNode";

/** The nodes already placed, ready for React Flow: keyboard-focusable, fixed for the mouse. */
export function toFlowNodes(
  nodes: SkillNodeView[],
  placed: Map<string, PositionedNode>,
  selectedId: string | null,
): SkillFlowNode[] {
  const result: SkillFlowNode[] = [];
  for (const node of nodes) {
    const spot = placed.get(node.id);
    if (!spot) continue;
    const selected = node.id === selectedId;
    result.push({
      id: node.id,
      type: "skill",
      position: { x: spot.x, y: spot.y },
      width: spot.width,
      height: spot.height,
      data: { name: node.name, level: node.level },
      selected,
      draggable: false,
      focusable: true,
      ariaRole: "button",
      ariaLabel: t("skills.graph.node", {
        name: node.name,
        level: t(`skills.level.${levelKey(node.level)}`),
      }),
      className:
        "rounded-md outline-none focus-visible:ring-3 focus-visible:ring-ring focus-visible:ring-offset-2",
      domAttributes: { "aria-pressed": selected },
    });
  }
  return result;
}

/** Prerequisite links whose two ends are on the graph: from prerequisite to dependent. */
export function toFlowEdges(edges: SkillEdgeView[], placed: Map<string, PositionedNode>): Edge[] {
  return edges
    .filter((edge) => placed.has(edge.beforeId) && placed.has(edge.afterId))
    .map((edge) => ({
      id: `${edge.beforeId}->${edge.afterId}`,
      source: edge.beforeId,
      target: edge.afterId,
      focusable: false,
      selectable: false,
      markerEnd: { type: MarkerType.ArrowClosed, color: "var(--muted-foreground)" },
      style: { stroke: "var(--muted-foreground)", strokeWidth: 1.5 },
    }));
}

/** React Flow's accessibility texts, in French. */
export function ariaLabels(): Partial<AriaLabelConfig> {
  return {
    "node.a11yDescription.default": t("skills.graph.a11y.node"),
    "node.a11yDescription.keyboardDisabled": t("skills.graph.a11y.node"),
    "node.a11yDescription.ariaLiveMessage": ({ direction }) =>
      t("skills.graph.a11y.moved", { direction }),
    "edge.a11yDescription.default": t("skills.graph.a11y.edge"),
    "controls.ariaLabel": t("skills.graph.a11y.controls"),
    "controls.zoomIn.ariaLabel": t("skills.graph.a11y.zoomIn"),
    "controls.zoomOut.ariaLabel": t("skills.graph.a11y.zoomOut"),
    "controls.fitView.ariaLabel": t("skills.graph.a11y.fitView"),
    "handle.ariaLabel": t("skills.graph.a11y.handle"),
  };
}
