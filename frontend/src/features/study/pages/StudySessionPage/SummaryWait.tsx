import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { LoadingState } from "@/shared/ui/states/LoadingState";

interface SummaryWaitProps {
  /** Le bilan met trop de temps (20 relectures sans résultat). */
  late: boolean;
  onRetry: () => void;
}

/** Attente du bilan : le Tuteur le rédige ; trop long, on le dit et on propose de relire. */
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
