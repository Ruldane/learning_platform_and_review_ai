import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { SkillGraph } from "../../components/SkillGraph";
import { useSkillGraph } from "../../hooks/useSkillGraph";
import { toGraphView } from "../../toView";
import { QueryPanel } from "./QueryPanel";
import { SkillDetailSlot } from "./SkillDetailSlot";

/** The goals: a goal (and its program) fills the map. */
const GOALS_PATH = "/learn/goals";

/** Gives focus back to the closed skill's node: the keyboard keeps its place. */
function focusNode(root: HTMLElement | null, skillId: string) {
  const nodes = root?.querySelectorAll<HTMLElement>(".react-flow__node") ?? [];
  Array.from(nodes)
    .find((node) => node.dataset.id === skillId)
    ?.focus();
}

/** The Graph tab: the map reread every 30 s; a node opens the skill's drawer. */
export function GraphPanel() {
  const query = useSkillGraph();
  const root = useRef<HTMLDivElement>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const view = useMemo(() => (query.data ? toGraphView(query.data) : null), [query.data]);
  const navigate = useNavigate();
  const toGoals = {
    label: t("skills.graph.emptyAction"),
    onClick: () => void navigate(GOALS_PATH),
  };

  const close = () => {
    const closing = selectedId;
    setSelectedId(null);
    if (closing !== null) focusNode(root.current, closing);
  };

  return (
    <div ref={root} className="flex flex-col gap-4">
      <QueryPanel query={query} loading={t("skills.page.loading")}>
        {() =>
          view ? (
            <SkillGraph
              nodes={view.nodes}
              edges={view.edges}
              selectedId={selectedId}
              onSelect={setSelectedId}
              emptyAction={toGoals}
            />
          ) : null
        }
      </QueryPanel>
      <SkillDetailSlot skillId={selectedId} onClose={close} />
    </div>
  );
}
