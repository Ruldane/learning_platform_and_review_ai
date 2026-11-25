import { formatCount, formatUsd } from "../format";
import type { CostRowView } from "../viewTypes";

export const NUMBER_CELL = "px-3 py-2 text-right tabular-nums whitespace-nowrap";

/**
 * A breakdown row: its label (with the agent's colour dot), then five
 * numbers.
 */
export function CostRow({ row }: { row: CostRowView }) {
  return (
    <tr className="border-b border-border last:border-0">
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
  );
}
