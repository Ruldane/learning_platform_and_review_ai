import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import type { SkillEdgeView, SkillNodeView } from "../viewTypes";
import { PlacedGraph } from "./PlacedGraph";

export interface SkillGraphProps {
  nodes: SkillNodeView[];
  edges: SkillEdgeView[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  /** The action of the empty state (rule 15.4: never a dead end). */
  emptyAction?: { label: string; onClick: () => void };
}

/**
 * Skill map: one node per skill (colour = level, size = market demand), one
 * link per prerequisite, left to right. Read-only: nodes do not move, but are
 * walked with Tab and opened with Enter or Space. The view pans and zooms with the
 * controls; the wheel keeps its page-scrolling role.
 */
export function SkillGraph(props: SkillGraphProps) {
  if (props.nodes.length === 0) {
    return (
      <EmptyState
        title={t("skills.graph.empty")}
        description={t("skills.graph.emptyHint")}
        action={props.emptyAction}
      />
    );
  }
  return <PlacedGraph {...props} />;
}
