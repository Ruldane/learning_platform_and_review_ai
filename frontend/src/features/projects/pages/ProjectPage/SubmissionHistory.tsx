import { t } from "@/shared/i18n/t";
import type { SubmissionItemView } from "../../toView";
import { SubmissionItem } from "./SubmissionItem";

/**
 * L'historique des rendus (le dernier d'abord) : date, lien du dépôt, description et miniatures des
 * captures, montrées telles quelles (le Praticien ne les lit pas).
 */
export function SubmissionHistory({ submissions }: { submissions: SubmissionItemView[] }) {
  return (
    <section aria-labelledby="project-history" className="flex flex-col gap-3">
      <h2 id="project-history" className="text-lg font-medium">
        {t("projects.page.history")}
      </h2>
      {submissions.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("projects.page.historyEmpty")}</p>
      ) : (
        <ol className="flex flex-col gap-3">
          {submissions.map((submission) => (
            <SubmissionItem key={submission.at} submission={submission} />
          ))}
        </ol>
      )}
    </section>
  );
}
