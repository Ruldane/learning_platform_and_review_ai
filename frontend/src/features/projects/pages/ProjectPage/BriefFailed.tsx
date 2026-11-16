import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { useRetryBrief } from "../../hooks/useRetryBrief";

/** L'énoncé n'a pas pu être écrit (trois essais) : le dire, et proposer « Réessayer l'énoncé ». */
export function BriefFailed({ projectId }: { projectId: string }) {
  const { retry, pending, error } = useRetryBrief(projectId);
  return (
    <section
      aria-label={t("projects.card.status.brief_failed")}
      className="flex flex-col items-start gap-3 rounded-xl border bg-card p-4 text-sm"
    >
      <p>{t("projects.page.briefFailed")}</p>
      <Button disabled={pending} onClick={retry}>
        {pending ? t("projects.page.retryingBrief") : t("projects.page.retryBrief")}
      </Button>
      {error ? <InlineError message={error} /> : null}
    </section>
  );
}
