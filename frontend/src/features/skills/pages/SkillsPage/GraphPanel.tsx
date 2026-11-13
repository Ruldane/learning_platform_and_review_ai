import { useMemo, useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import { SkillGraph } from "../../components/SkillGraph";
import { useSkillGraph } from "../../hooks/useSkillGraph";
import { toGraphView } from "../../toView";
import { QueryPanel } from "./QueryPanel";
import { SkillDetailSlot } from "./SkillDetailSlot";

/** Rend le focus au nœud de la compétence refermée (le clavier retrouve sa place dans le graphe). */
function focusNode(root: HTMLElement | null, skillId: string) {
  const nodes = root?.querySelectorAll<HTMLElement>(".react-flow__node") ?? [];
  Array.from(nodes)
    .find((node) => node.dataset.id === skillId)
    ?.focus();
}

/** L'onglet Graphe : la carte relue toutes les 30 s ; un nœud ouvre le tiroir de la compétence. */
export function GraphPanel() {
  const query = useSkillGraph();
  const root = useRef<HTMLDivElement>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const view = useMemo(() => (query.data ? toGraphView(query.data) : null), [query.data]);

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
            />
          ) : null
        }
      </QueryPanel>
      <SkillDetailSlot skillId={selectedId} onClose={close} />
    </div>
  );
}
