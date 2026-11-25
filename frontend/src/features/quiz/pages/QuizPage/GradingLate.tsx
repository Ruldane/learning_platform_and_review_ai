import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

/** Grading takes longer than expected (90 re-reads): offer to re-read the grade. */
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
