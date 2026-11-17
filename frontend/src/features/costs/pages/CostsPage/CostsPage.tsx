import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { CostByDayChart } from "../../components/CostByDayChart";
import { CostTable } from "../../components/CostTable";
import { CostTotalsCard } from "../../components/CostTotalsCard";
import type { CostWindow } from "../../components/viewTypes";
import { WindowPicker } from "../../components/WindowPicker";
import { useCosts } from "../../hooks/useCosts";

const DEFAULT_WINDOW: CostWindow = 30;

/**
 * Réglages > Coûts : jetons et coût des appels aux modèles sur 7, 30 ou 90 jours, avec le total,
 * le coût par jour (barres et tableau équivalent) et les répartitions par feature, agent, modèle.
 * La fenêtre reste affichée pendant la lecture : le focus ne quitte pas le bouton choisi.
 */
export function CostsPage() {
  const [days, setDays] = useState<CostWindow>(DEFAULT_WINDOW);
  const costs = useCosts(days);
  const report = costs.data;
  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold">{t("costs.report.title")}</h1>
        <p className="mt-1 text-muted-foreground">{t("costs.report.intro")}</p>
      </header>
      <WindowPicker value={days} onChange={setDays} />
      {costs.isPending ? <LoadingState label={t("costs.report.loading")} /> : null}
      {costs.isError ? (
        <ErrorState message={errorMessage(costs.error)} onRetry={() => void costs.refetch()} />
      ) : null}
      {report && report.total.calls === 0 ? (
        <EmptyState
          title={t("costs.report.empty.title", { days: report.days })}
          description={t("costs.report.empty.description")}
        />
      ) : null}
      {report && report.total.calls > 0 ? (
        <>
          <CostTotalsCard days={report.days} totals={report.total} />
          <CostByDayChart
            rows={report.byDay}
            since={report.since}
            until={report.until}
            totalCostUsd={report.total.costUsd}
          />
          <CostTable
            title={t("costs.report.byFeature.title")}
            firstColumn={t("costs.report.byFeature.first")}
            rows={report.byFeature}
          />
          <CostTable
            title={t("costs.report.byAgent.title")}
            firstColumn={t("costs.report.byAgent.first")}
            rows={report.byAgent}
          />
          <CostTable
            title={t("costs.report.byModel.title")}
            firstColumn={t("costs.report.byModel.first")}
            rows={report.byModel}
          />
        </>
      ) : null}
    </div>
  );
}
