import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { CostRowView } from "../viewTypes";
import { CostRow, NUMBER_CELL } from "./CostRow";

interface CostTableProps {
  title: string;
  /** The header of the first column (« Feature », « Agent », « Modèle »). */
  firstColumn: string;
  rows: CostRowView[];
}

const COLUMNS = ["calls", "tokensIn", "tokensOut", "cost", "estimated"] as const;

/** A breakdown table: calls, input and output tokens, cost, estimated calls. */
export function CostTable({ title, firstColumn, rows }: CostTableProps) {
  const titleId = useId();
  return (
    <div className="flex flex-col gap-2">
      <h2 id={titleId} className="text-lg font-semibold">
        {title}
      </h2>
      <div
        role="region"
        aria-labelledby={titleId}
        tabIndex={0}
        className="overflow-x-auto rounded-xl border border-border bg-card"
      >
        <table aria-labelledby={titleId} className="w-full text-sm">
          <thead className="border-b border-border text-left">
            <tr>
              <th scope="col" className="px-3 py-2 font-medium">
                {firstColumn}
              </th>
              {COLUMNS.map((column) => (
                <th key={column} scope="col" className={`${NUMBER_CELL} font-medium`}>
                  {t(`costs.columns.${column}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <CostRow key={row.key} row={row} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
