import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { useRetryBrief } from "../../hooks/useRetryBrief";

/** L'énoncé n'a pas pu être écrit (trois essais) : le dire, et proposer « Réessayer l'énoncé ». */
export function BriefFailed({
  projectId,
  onRetried,
}: {
  projectId: string;
  /** L'énoncé est relancé : la section va disparaître, la page reporte le focus sur le suivi. */
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
