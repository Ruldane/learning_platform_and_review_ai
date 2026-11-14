import { useMemo, useState } from "react";
import { GapTable } from "../../components/GapTable";
import { MatchScore } from "../../components/MatchScore";
import { isAddable, MAX_PLAN_SKILLS } from "../../components/viewTypes";
import { usePlanGap } from "../../hooks/usePlanGap";
import { toGapRows } from "../../toView";
import type { GapOut } from "../../types";
import { PlanResult } from "./PlanResult";

/**
 * L'écart prêt : le score (s'il existe), le tableau et « Ajouter au planning ». On ne coche que
 * des compétences qui manquent vraiment, dix au plus ; une case dont la ligne a changé à la
 * relecture est retirée de la sélection d'office.
 */
export function GapReady({ postingId, gap }: { postingId: string; gap: GapOut }) {
  const [selected, setSelected] = useState<string[]>([]);
  const planner = usePlanGap(postingId, () => setSelected([]));
  const rows = useMemo(() => toGapRows(gap.rows), [gap.rows]);
  const chosen = useMemo(() => {
    const addable = new Set(rows.filter(isAddable).map((row) => row.skill));
    return selected.filter((skill) => addable.has(skill));
  }, [rows, selected]);

  const toggle = (skill: string) =>
    setSelected((current) => {
      if (current.includes(skill)) return current.filter((name) => name !== skill);
      return current.length >= MAX_PLAN_SKILLS ? current : [...current, skill];
    });

  return (
    <div className="flex flex-col gap-4">
      {gap.score === null ? null : <MatchScore score={gap.score} />}
      <GapTable
        rows={rows}
        selected={chosen}
        onToggle={toggle}
        onAddToPlan={() => planner.plan(chosen)}
        adding={planner.pending}
      />
      <PlanResult outcome={planner.outcome} failure={planner.failure} />
    </div>
  );
}
