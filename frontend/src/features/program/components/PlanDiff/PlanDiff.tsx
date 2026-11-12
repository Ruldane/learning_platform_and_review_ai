import { t } from "@/shared/i18n/t";
import { shortDay } from "../format";
import type { PlanDiffTask, PlanDiffView } from "../viewTypes";
import { DiffEntry } from "./DiffEntry";
import { DiffSection } from "./DiffSection";

interface PlanDiffProps {
  diff: PlanDiffView;
}

function plannedEntry(task: PlanDiffTask) {
  return (
    <DiffEntry
      key={task.id}
      title={task.title}
      moduleTitle={task.moduleTitle}
      detail={t("program.diff.plannedOn", { day: shortDay(task.plannedDate) })}
    />
  );
}

/** Changements d'un programme : tâches ajoutées, retirées et déplacées (avant → après). */
export function PlanDiff({ diff }: PlanDiffProps) {
  if (diff.added.length + diff.removed.length + diff.moved.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("program.diff.empty")}</p>;
  }
  return (
    <div role="group" aria-label={t("program.diff.label")} className="flex flex-col gap-4">
      <DiffSection title={t("program.diff.added")} count={diff.added.length}>
        {diff.added.map(plannedEntry)}
      </DiffSection>
      <DiffSection title={t("program.diff.removed")} count={diff.removed.length}>
        {diff.removed.map(plannedEntry)}
      </DiffSection>
      <DiffSection title={t("program.diff.moved")} count={diff.moved.length}>
        {diff.moved.map((move) => (
          <DiffEntry
            key={move.id}
            title={move.title}
            moduleTitle={move.moduleTitle}
            detail={t("program.diff.movedRange", {
              from: shortDay(move.from),
              to: shortDay(move.to),
            })}
          />
        ))}
      </DiffSection>
    </div>
  );
}
