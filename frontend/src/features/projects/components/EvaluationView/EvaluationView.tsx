import { t } from "@/shared/i18n/t";
import type { EvaluationDataView } from "../viewTypes";
import { CriteriaChecklist } from "../CriteriaChecklist";

interface EvaluationViewProps {
  evaluation: EvaluationDataView;
  /** The brief's criteria: each one is shown, with the result carrying its number. */
  criteria: string[];
}

/**
 * The Practitioner's evaluation: the verdict (computed by the code), its comment, the state of
 * the repository read, each criterion of the brief (linked to its result by that result's
 * `index`, never by its position) and the note that screenshots were not read.
 */
export function EvaluationView({ evaluation, criteria }: EvaluationViewProps) {
  const validated = evaluation.verdict === "validated";
  return (
    <section
      aria-labelledby="project-evaluation"
      className="flex flex-col gap-3 rounded-xl border bg-card p-4 text-sm"
    >
      <h2 id="project-evaluation" className="text-lg font-medium">
        {t("projects.evaluation.title")}
      </h2>
      <p
        data-verdict={evaluation.verdict}
        className={`font-medium ${validated ? "text-emerald-700 dark:text-emerald-400" : "text-destructive"}`}
      >
        {t(`projects.evaluation.verdict.${evaluation.verdict}`)}
      </p>
      <p>{evaluation.feedback}</p>
      <CriteriaChecklist criteria={criteria} results={evaluation.results} />
      <p className="text-muted-foreground">
        {t(`projects.evaluation.repo.${evaluation.repoStatus}`)}
      </p>
      {evaluation.hasScreenshots ? (
        <p className="text-muted-foreground">{t("projects.evaluation.screenshotsUnread")}</p>
      ) : null}
    </section>
  );
}
