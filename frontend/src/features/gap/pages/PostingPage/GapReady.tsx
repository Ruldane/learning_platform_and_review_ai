import { useMemo, useState } from "react";
import { GapTable } from "../../components/GapTable";
import { MatchScore } from "../../components/MatchScore";
import { canPlan, isAddable, MAX_PLAN_SKILLS } from "../../components/viewTypes";
import { usePlanGap } from "../../hooks/usePlanGap";
import { useValidateGap } from "../../hooks/useValidateGap";
import { InlineError } from "@/shared/ui/states/InlineError";
import { useLaunchSource } from "@/shared/session-ui";
import { toGapRows } from "../../toView";
import type { GapOut } from "../../types";
import { PlanResult } from "./PlanResult";
import { ProgramPicker } from "./ProgramPicker";

export function GapReady({ postingId, gap }: { postingId: string; gap: GapOut }) {
  const [selected, setSelected] = useState<string[]>([]);
  const [programId, setProgramId] = useState<string>();
  const provider = useLaunchSource();
  const planner = usePlanGap(postingId, () => setSelected([]), provider.source);
  const validator = useValidateGap(postingId, provider.source);
  const rows = useMemo(() => toGapRows(gap.rows), [gap.rows]);
  const available = new Set(rows.filter(canPlan).map((row) => row.skill));
  const chosen = selected.filter((skill) => available.has(skill));
  const eligible = new Set(rows.filter(isAddable).map((row) => row.skill));

  const toggle = (skill: string) =>
    setSelected((current) => {
      if (current.includes(skill)) return current.filter((name) => name !== skill);
      return current.length >= MAX_PLAN_SKILLS ? current : [...current, skill];
    });

  return (
    <div className="flex flex-col gap-4">
      {gap.score === null ? null : <MatchScore score={gap.score} />}
      <ProgramPicker value={programId} onChange={setProgramId} disabled={planner.pending} />
      <GapTable
        rows={rows}
        selected={chosen}
        onToggle={toggle}
        launchOptions={provider.menu}
        onAddToPlan={() => planner.plan(chosen, programId)}
        onValidate={() => validator.validate(chosen.filter((skill) => eligible.has(skill)))}
        adding={planner.pending || validator.pending}
      />
      {validator.failure ? <InlineError message={validator.failure} /> : null}
      <PlanResult outcome={planner.outcome} failure={planner.failure} />
    </div>
  );
}
