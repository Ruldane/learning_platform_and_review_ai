import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { GoalRow } from "../viewTypes";

interface GoalListProps {
  goals: GoalRow[];
}

const DATE = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" });

function formatDay(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  return DATE.format(new Date(year ?? 0, (month ?? 1) - 1, day ?? 1));
}

/** Lien vers le programme : celui de l'objectif s'il existe, sinon le plus récent. */
const programPath = (goal: GoalRow) =>
  goal.programId ? `/apprendre/programme/${goal.programId}` : "/apprendre/programme";

/**
 * Les objectifs de January : texte, poste visé, échéance, heures par semaine, statut, lien vers le
 * Conseil et, une fois un parcours choisi, vers le programme.
 */
export function GoalList({ goals }: GoalListProps) {
  return (
    <ul aria-label={t("learning.goals.list.label")} className="flex flex-col gap-3">
      {goals.map((goal) => (
        <li
          key={goal.id}
          className="flex flex-col gap-2 rounded-xl border border-border bg-card px-4 py-3"
        >
          <p className="font-medium break-words">{goal.text}</p>
          <p className="text-sm text-primary">{t(`learning.goals.list.status.${goal.status}`)}</p>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
            {goal.targetRole ? <span>{goal.targetRole}</span> : null}
            {goal.deadline ? (
              <span>{t("learning.goals.list.deadline", { date: formatDay(goal.deadline) })}</span>
            ) : null}
            {goal.weeklyHours ? (
              <span>{t("learning.goals.list.hours", { hours: goal.weeklyHours })}</span>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-4 text-sm">
            <Link
              to={`/apprendre/objectifs/${goal.id}/conseil`}
              className="underline underline-offset-2"
            >
              {t("learning.goals.list.council")}
              <span className="sr-only"> : {goal.text}</span>
            </Link>
            {goal.status === "council" ? null : (
              <Link to={programPath(goal)} className="underline underline-offset-2">
                {t("learning.goals.list.program")}
                <span className="sr-only"> : {goal.text}</span>
              </Link>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
