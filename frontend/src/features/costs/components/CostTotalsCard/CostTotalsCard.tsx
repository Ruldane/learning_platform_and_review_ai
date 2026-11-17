import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { formatCount, formatUsd } from "../format";
import type { CostTotalsView } from "../viewTypes";
import { Figure } from "./Figure";

interface CostTotalsCardProps {
  days: number;
  totals: CostTotalsView;
}

/** Le total de la fenêtre : appels (dont estimés), jetons entrants et sortants, coût. */
export function CostTotalsCard({ days, totals }: CostTotalsCardProps) {
  const titleId = useId();
  const estimated = totals.estimatedCalls;
  const estimatedKey =
    estimated === 1 ? "costs.report.totals.estimatedOne" : "costs.report.totals.estimated";
  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4"
    >
      <h2 id={titleId} className="text-lg font-semibold">
        {t("costs.report.totals.title", { days })}
      </h2>
      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Figure label={t("costs.report.totals.calls")}>
          {formatCount(totals.calls)}
          {estimated > 0 ? (
            <span className="block text-sm font-normal text-muted-foreground">
              {t(estimatedKey, { count: formatCount(estimated) })}
            </span>
          ) : null}
        </Figure>
        <Figure label={t("costs.report.totals.tokensIn")}>{formatCount(totals.tokensIn)}</Figure>
        <Figure label={t("costs.report.totals.tokensOut")}>{formatCount(totals.tokensOut)}</Figure>
        <Figure label={t("costs.report.totals.cost")}>{formatUsd(totals.costUsd)}</Figure>
      </dl>
    </section>
  );
}
