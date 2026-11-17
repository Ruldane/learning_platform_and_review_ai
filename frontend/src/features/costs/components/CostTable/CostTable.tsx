import { useId } from "react";
import { formatCount, formatUsd } from "../format";
import { t } from "@/shared/i18n/t";
import type { CostRowView } from "../viewTypes";

interface CostTableProps {
  title: string;
  /** L'en-tête de la première colonne (« Feature », « Agent », « Modèle »). */
  firstColumn: string;
  rows: CostRowView[];
}

const NUMBER_CELL = "px-3 py-2 text-right tabular-nums";

/** Un tableau de répartition : appels, jetons entrants et sortants, coût, appels estimés. */
export function CostTable({ title, firstColumn, rows }: CostTableProps) {
  const titleId = useId();
  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-2">
      <h2 id={titleId} className="text-lg font-semibold">
        {title}
      </h2>
      <div className="overflow-x-auto rounded-xl border border-border bg-card">
        <table aria-labelledby={titleId} className="w-full text-sm">
          <thead className="border-b border-border text-left">
            <tr>
              <th scope="col" className="px-3 py-2 font-medium">
                {firstColumn}
              </th>
              {(["calls", "tokensIn", "tokensOut", "cost", "estimated"] as const).map((column) => (
                <th key={column} scope="col" className={`${NUMBER_CELL} font-medium`}>
                  {t(`costs.columns.${column}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} className="border-b border-border last:border-0">
                <th scope="row" className="px-3 py-2 text-left font-normal">
                  <span className="inline-flex items-center gap-2">
                    {row.color ? (
                      <span
                        aria-hidden="true"
                        className="size-2.5 shrink-0 rounded-full"
                        style={{ backgroundColor: row.color }}
                      />
                    ) : null}
                    {row.label}
                  </span>
                </th>
                <td className={NUMBER_CELL}>{formatCount(row.calls)}</td>
                <td className={NUMBER_CELL}>{formatCount(row.tokensIn)}</td>
                <td className={NUMBER_CELL}>{formatCount(row.tokensOut)}</td>
                <td className={NUMBER_CELL}>{formatUsd(row.costUsd)}</td>
                <td className={NUMBER_CELL}>{formatCount(row.estimatedCalls)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
