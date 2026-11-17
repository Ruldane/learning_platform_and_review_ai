import { t } from "@/shared/i18n/t";
import { shortDay } from "@/shared/lib/format";
import { formatCount, formatUsd } from "../format";
import type { CostRowView } from "../viewTypes";

/**
 * Le tableau équivalent du graphique, un jour par ligne : masqué à l'œil (`sr-only`), lu par les
 * lecteurs d'écran à la place du dessin.
 */
export function DayTable({ rows }: { rows: CostRowView[] }) {
  return (
    <table className="sr-only">
      <caption>{t("costs.report.chart.tableCaption")}</caption>
      <thead>
        <tr>
          <th scope="col">{t("costs.report.chart.day")}</th>
          <th scope="col">{t("costs.columns.calls")}</th>
          <th scope="col">{t("costs.columns.tokensIn")}</th>
          <th scope="col">{t("costs.columns.tokensOut")}</th>
          <th scope="col">{t("costs.columns.cost")}</th>
          <th scope="col">{t("costs.columns.estimated")}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.key}>
            <th scope="row">{shortDay(row.key)}</th>
            <td>{formatCount(row.calls)}</td>
            <td>{formatCount(row.tokensIn)}</td>
            <td>{formatCount(row.tokensOut)}</td>
            <td>{formatUsd(row.costUsd)}</td>
            <td>{formatCount(row.estimatedCalls)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
