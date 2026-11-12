import { useMemo } from "react";
import { t } from "@/shared/i18n/t";
import { PlanDiff } from "../../components/PlanDiff";
import { useTaskMutations } from "../../hooks/useTaskMutations";
import { toModuleLessons, toPlanDiffView, toProgressView, toWeekViews } from "../../toView";
import type { ProgramOut } from "../../types";
import { ProgramHeader } from "./ProgramHeader";
import { ProgramViews } from "./ProgramViews";
import { ValidationBar } from "./ValidationBar";
import { useValidationFlow } from "./useValidationFlow";

/** Aujourd'hui, `AAAA-MM-JJ` (heure locale). */
function todayIso(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${String(now.getDate()).padStart(2, "0")}`;
}

/** Un programme chargé : en-tête, validation du brouillon, changements de version et trois vues. */
export function ProgramScreen({ program }: { program: ProgramOut }) {
  const edits = useTaskMutations(program.id);
  const flow = useValidationFlow(program);
  const weeks = useMemo(
    () =>
      toWeekViews(program, { weekday: program.weekday_minutes, weekend: program.weekend_minutes }),
    [program],
  );
  const diff = useMemo(
    () => (program.diff ? toPlanDiffView(program.diff, program) : null),
    [program],
  );
  return (
    <div className="flex flex-col gap-6">
      <ProgramHeader program={program} />
      <ValidationBar flow={flow} />
      {diff ? (
        <section aria-labelledby="program-changes-title" className="flex flex-col gap-2">
          <h2 id="program-changes-title" className="text-lg font-semibold">
            {t("program.changes.heading")}
          </h2>
          <PlanDiff diff={diff} />
        </section>
      ) : null}
      <ProgramViews
        weeks={weeks}
        progress={toProgressView(program.progress)}
        lessons={toModuleLessons(program)}
        edits={edits}
        today={todayIso()}
      />
    </div>
  );
}
