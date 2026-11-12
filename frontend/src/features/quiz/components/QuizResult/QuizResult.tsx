import { t } from "@/shared/i18n/t";
import type { AttemptResultView } from "../viewTypes";
import { FollowupSection } from "./FollowupSection";
import { QuestionResult } from "./QuestionResult";
import { formatPoints } from "./points";

/**
 * Le résultat d'une tentative : le pourcentage, « Acquis validé » quand le quiz passe (80 %), les
 * points, le détail de chaque question puis, après un échec, révisions et nouvel essai.
 */
export function QuizResult({ result }: { result: AttemptResultView }) {
  const earned = result.results.reduce((sum, item) => sum + item.points, 0);
  const ordered = [...result.results].sort((a, b) => a.rank - b.rank);
  return (
    <section className="flex flex-col gap-4">
      <div className="rounded-xl border bg-card p-4">
        <h2 className="text-lg font-semibold">{t("quiz.result.title")}</h2>
        <p className="mt-1 text-3xl font-semibold tabular-nums">
          {t("quiz.result.score", { score: result.score })}
        </p>
        <p className={result.passed ? "font-medium text-primary" : "text-sm text-muted-foreground"}>
          {t(result.passed ? "quiz.result.passed" : "quiz.result.notPassed")}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {t("quiz.result.points", {
            points: formatPoints(earned),
            max: formatPoints(result.results.length),
          })}
        </p>
      </div>
      <ul aria-label={t("quiz.result.questions")} className="flex flex-col gap-3">
        {ordered.map((item) => (
          <QuestionResult key={item.questionId} result={item} />
        ))}
      </ul>
      {result.followup !== null ? <FollowupSection followup={result.followup} /> : null}
    </section>
  );
}
