import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { LoadingState } from "@/shared/ui/states/LoadingState";

interface SummaryWaitProps {
  /** The summary takes too long (20 rereads without a result). */
  late: boolean;
  onRetry: () => void;
}

/** Waiting for the summary: the Tutor writes it; if too long, we say so and offer to reread. */
export function SummaryWait({ late, onRetry }: SummaryWaitProps) {
  if (!late) return <LoadingState label={t("study.session.writingSummary")} />;
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-3 py-2"
    >
      <p className="text-sm">{t("study.session.summaryLate")}</p>
      <Button variant="outline" onClick={onRetry}>
        {t("study.session.retrySummary")}
      </Button>
    </div>
  );
}
