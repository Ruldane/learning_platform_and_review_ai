import { t } from "@/shared/i18n/t";
import type { AttemptSummaryOut } from "../../types";
import { percent } from "../../toView";

function labelOf(attempt: AttemptSummaryOut): string {
  if (attempt.status === "graded" && attempt.score !== null) {
    return t("quiz.page.historyItem", { score: percent(attempt.score) });
  }
  return t(attempt.status === "grading" ? "quiz.page.historyGrading" : "quiz.page.historyFailed");
}

/** Les essais déjà faits, du plus ancien au plus récent ; rien tant qu'il n'y en a pas. */
export function AttemptHistory({ attempts }: { attempts: AttemptSummaryOut[] }) {
  if (attempts.length === 0) return null;
  const ordered = [...attempts].sort((a, b) => a.created_at.localeCompare(b.created_at));
  return (
    <section aria-label={t("quiz.page.history")} className="text-sm text-muted-foreground">
      <h2 className="inline font-medium">{t("quiz.page.history")} : </h2>
      <ul className="inline">
        {ordered.map((attempt, index) => (
          <li key={attempt.id} className="inline">
            {index > 0 ? ", " : ""}
            {labelOf(attempt)}
          </li>
        ))}
      </ul>
    </section>
  );
}
