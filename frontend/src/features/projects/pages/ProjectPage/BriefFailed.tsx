import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { useRetryBrief } from "../../hooks/useRetryBrief";

/** The brief could not be written (three attempts): say so, and offer « Réessayer l'énoncé ». */
export function BriefFailed({
  projectId,
  onRetried,
}: {
  projectId: string;
  /** The brief is retried: the section will vanish, so focus moves to the tracker. */
  onRetried: () => void;
}) {
  const { retry, pending, error, launchMenu } = useRetryBrief(projectId, onRetried);
  return (
    <section
      aria-label={t("projects.card.status.brief_failed")}
      className="flex flex-col items-start gap-3 rounded-xl border bg-card p-4 text-sm"
    >
      <p>{t("projects.page.briefFailed")}</p>
      {launchMenu}
      <Button aria-disabled={pending} onClick={() => !pending && retry()}>
        {pending ? t("projects.page.retryingBrief") : t("projects.page.retryBrief")}
      </Button>
      {error ? <InlineError message={error} /> : null}
    </section>
  );
}
