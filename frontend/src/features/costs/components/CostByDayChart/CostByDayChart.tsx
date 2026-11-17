import { useId } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { t } from "@/shared/i18n/t";
import { shortDay } from "@/shared/lib/format";
import { dayMonth, formatUsd, formatUsdTick } from "../format";
import type { CostRowView } from "../viewTypes";
import { DayTable } from "./DayTable";

interface CostByDayChartProps {
  /** Un jour par ligne (`key` : `AAAA-MM-JJ`), les jours sans appel à zéro. */
  rows: CostRowView[];
  since: string;
  until: string;
  totalCostUsd: number;
}

/**
 * Le coût de chaque jour en barres. Le dessin est une image nommée pour les lecteurs d'écran, qui
 * lisent à sa place le tableau équivalent (un jour par ligne) ; les barres ne s'animent pas.
 */
export function CostByDayChart({ rows, since, until, totalCostUsd }: CostByDayChartProps) {
  const titleId = useId();
  const data = rows.map((row) => ({ day: row.key, cost: row.costUsd }));
  const label = t("costs.report.chart.label", {
    since: shortDay(since),
    until: shortDay(until),
    total: formatUsd(totalCostUsd),
  });
  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-2">
      <h2 id={titleId} className="text-lg font-semibold">
        {t("costs.report.chart.title")}
      </h2>
      <div
        role="img"
        aria-label={label}
        className="h-64 w-full rounded-xl border border-border bg-card p-2"
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="3 3" />
            <XAxis dataKey="day" tickFormatter={dayMonth} minTickGap={16} />
            <YAxis tickFormatter={formatUsdTick} width={72} />
            <Tooltip
              labelFormatter={(day) => shortDay(String(day))}
              formatter={(value) => formatUsd(Number(value))}
            />
            <Bar
              dataKey="cost"
              name={t("costs.report.chart.series")}
              fill="var(--primary)"
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <DayTable rows={rows} />
    </section>
  );
}
