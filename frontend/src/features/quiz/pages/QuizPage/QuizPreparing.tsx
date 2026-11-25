import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { LoadingState } from "@/shared/ui/states/LoadingState";

interface QuizPreparingProps {
  /** The preparation takes longer than expected (40 re-reads with no result). */
  late: boolean;
  onKeepWaiting: () => void;
}

/** The quiz is being prepared: a loading state; if too long, say so and offer to wait longer. */
export function QuizPreparing({ late, onKeepWaiting }: QuizPreparingProps) {
  if (!late) return <LoadingState label={t("quiz.page.preparing")} />;
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-3 py-2"
    >
      <p className="text-sm">{t("quiz.page.preparingLate")}</p>
      <Button variant="outline" onClick={onKeepWaiting}>
        {t("quiz.page.keepWaiting")}
      </Button>
    </div>
  );
}
