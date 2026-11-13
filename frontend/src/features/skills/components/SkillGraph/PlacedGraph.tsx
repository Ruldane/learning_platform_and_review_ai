import { Controls, ReactFlow, type NodeTypes } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo, type KeyboardEvent } from "react";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { SkillLegend } from "../SkillLegend";
import { SkillNode } from "./SkillNode";
import type { SkillGraphProps } from "./SkillGraph";
import { ariaLabels, toFlowEdges, toFlowNodes } from "./toFlow";
import { useGraphLayout } from "./useGraphLayout";

const NODE_TYPES: NodeTypes = { skill: SkillNode };
const FIT_VIEW = { padding: 0.15, duration: 0 };

/** Entrée ou Espace sur un nœud focalisé : sélectionne la compétence (React Flow n'appelle pas `onNodeClick`). */
function selectWithKeyboard(event: KeyboardEvent<HTMLDivElement>, onSelect: (id: string) => void) {
  if (event.key !== "Enter" && event.key !== " ") return;
  const node = (event.target as HTMLElement).closest<HTMLElement>(".react-flow__node");
  const id = node?.dataset.id;
  if (!node || !id || event.target !== node) return;
  event.preventDefault();
  onSelect(id);
}

/** Le graphe non vide : mise en page (elkjs), puis React Flow. */
export function PlacedGraph({ nodes, edges, selectedId, onSelect }: SkillGraphProps) {
  const { placed, failed } = useGraphLayout(nodes, edges);
  const flowNodes = useMemo(
    () => (placed ? toFlowNodes(nodes, placed, selectedId) : []),
    [nodes, placed, selectedId],
  );
  const flowEdges = useMemo(() => (placed ? toFlowEdges(edges, placed) : []), [edges, placed]);

  return (
    <section aria-label={t("skills.graph.label")} className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">{t("skills.graph.hint")}</p>
      {failed ? <InlineError message={t("skills.graph.layoutFailed")} /> : null}
      {!placed && !failed ? <LoadingState label={t("skills.graph.layouting")} /> : null}
      {placed ? (
        <div
          className="h-[30rem] w-full rounded-xl border bg-card"
          onKeyDown={(event) => selectWithKeyboard(event, onSelect)}
        >
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={NODE_TYPES}
            onNodeClick={(_, node) => onSelect(node.id)}
            nodesDraggable={false}
            nodesConnectable={false}
            nodesFocusable
            edgesFocusable={false}
            elementsSelectable={false}
            zoomOnScroll={false}
            preventScrolling={false}
            minZoom={0.3}
            maxZoom={1.5}
            fitView
            fitViewOptions={FIT_VIEW}
            ariaLabelConfig={ariaLabels()}
          >
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      ) : null}
      <SkillLegend />
    </section>
  );
}
