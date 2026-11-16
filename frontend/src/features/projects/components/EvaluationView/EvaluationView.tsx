import { t } from "@/shared/i18n/t";
import type { EvaluationDataView } from "../viewTypes";
import { CriteriaChecklist } from "../CriteriaChecklist";

interface EvaluationViewProps {
  evaluation: EvaluationDataView;
  /** Les critères de l'énoncé : chacun est montré, avec le résultat qui porte son numéro. */
  criteria: string[];
}

/**
 * L'évaluation du Praticien : le verdict (calculé par le code), son commentaire, l'état de la
 * lecture du dépôt, chaque critère de l'énoncé (rattaché à son résultat par l'`index` de celui-ci,
 * jamais par sa place) et la mention que les captures n'ont pas été lues.
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
