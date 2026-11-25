import { t } from "@/shared/i18n/t";
import type { SubmissionItemView } from "../../toView";
import { SubmissionItem } from "./SubmissionItem";

/**
 * The submission history (latest first): date, repository link, description and thumbnails of the
 * screenshots, shown as they are (the Practitioner does not read them).
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
