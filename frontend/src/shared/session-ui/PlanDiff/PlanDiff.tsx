import { t } from "@/shared/i18n/t";
import { shortDay } from "@/shared/lib/format";
import { DiffEntry } from "./DiffEntry";
import { DiffSection } from "./DiffSection";
import type { PlanDiffTask, PlanDiffView } from "./types";

interface PlanDiffProps {
  diff: PlanDiffView;
}

function plannedEntry(task: PlanDiffTask) {
  return (
    <DiffEntry
      key={task.id}
      title={task.title}
      moduleTitle={task.moduleTitle}
      detail={
        task.plannedDate ? t("session.diff.plannedOn", { day: shortDay(task.plannedDate) }) : null
      }
    />
  );
}

/**
 * Changements d'un programme : tâches ajoutées, retirées et déplacées (avant → après). Partagé par
 * le programme (diff de version) et la replanification (avant / après).
 */
export function PlanDiff({ diff }: PlanDiffProps) {
  if (diff.added.length + diff.removed.length + diff.moved.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("session.diff.empty")}</p>;
  }
  return (
    <div role="group" aria-label={t("session.diff.label")} className="flex flex-col gap-4">
      <DiffSection title={t("session.diff.added")} count={diff.added.length}>
        {diff.added.map(plannedEntry)}
      </DiffSection>
      <DiffSection title={t("session.diff.removed")} count={diff.removed.length}>
        {diff.removed.map(plannedEntry)}
      </DiffSection>
      <DiffSection title={t("session.diff.moved")} count={diff.moved.length}>
        {diff.moved.map((move) => (
          <DiffEntry
            key={move.id}
            title={move.title}
            moduleTitle={move.moduleTitle}
            detail={t("session.diff.movedRange", {
              from: shortDay(move.from),
              to: shortDay(move.to),
            })}
          />
        ))}
      </DiffSection>
    </div>
  );
}
