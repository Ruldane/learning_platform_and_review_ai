import { t } from "@/shared/i18n/t";
import type { CallView } from "../viewTypes";
import { CallRow } from "./CallRow";

const COLUMNS = [
  "at",
  "agent",
  "graph",
  "model",
  "tokensIn",
  "tokensOut",
  "latency",
  "cost",
  "session",
] as const;
const NUMERIC = new Set<string>(["tokensIn", "tokensOut", "latency", "cost"]);

/** The calls table, scrolling on narrow screens. */
export function CallTable({ calls }: { calls: CallView[] }) {
  return (
    <div
      role="region"
      aria-label={t("costs.log.tableCaption")}
      tabIndex={0}
      className="overflow-x-auto rounded-xl border border-border bg-card"
    >
      <table className="w-full text-sm">
        <caption className="sr-only">{t("costs.log.tableCaption")}</caption>
        <thead className="border-b border-border text-left">
          <tr>
            {COLUMNS.map((column) => (
              <th
                key={column}
                scope="col"
                className={`px-3 py-2 font-medium ${NUMERIC.has(column) ? "text-right" : ""}`}
              >
                {t(`costs.log.columns.${column}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {calls.map((call) => (
            <CallRow key={call.id} call={call} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
