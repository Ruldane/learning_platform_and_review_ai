import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

/** La correction prend plus de temps que prévu (90 relectures) : proposer de relire la note. */
export function GradingLate({ onKeepWaiting }: { onKeepWaiting: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-3 py-2"
    >
      <p className="text-sm">{t("quiz.page.gradingLate")}</p>
      <Button variant="outline" onClick={onKeepWaiting}>
        {t("quiz.page.keepGrading")}
      </Button>
    </div>
  );
}
