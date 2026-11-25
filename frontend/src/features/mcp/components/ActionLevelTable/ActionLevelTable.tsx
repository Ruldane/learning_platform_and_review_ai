import { useMemo, useState } from "react";
import { t } from "@/shared/i18n/t";
import type { ActionView } from "../viewTypes";
import { ActionRow } from "./ActionRow";
import { FeatureFilter } from "./FeatureFilter";

const COLUMNS = ["name", "feature", "level", "kind", "summary"] as const;

/**
 * The read-only table of exposed tools and their level, filterable by feature. Level
 * 4 has no row: it is never exposed, and the page says so below.
 */
export function ActionLevelTable({ actions }: { actions: ActionView[] }) {
  const [feature, setFeature] = useState("");
  const features = useMemo(() => {
    const seen = new Map(actions.map((action) => [action.feature, action.featureLabel]));
    return [...seen].map(([value, label]) => ({ value, label }));
  }, [actions]);
  const shown = feature ? actions.filter((action) => action.feature === feature) : actions;
  return (
    <div className="flex flex-col gap-3">
      <FeatureFilter value={feature} options={features} onChange={setFeature} />
      <div
        role="region"
        aria-label={t("mcp.levels.table")}
        tabIndex={0}
        className="overflow-x-auto rounded-xl border border-border bg-card"
      >
        <table className="w-full text-sm">
          <caption className="sr-only">{t("mcp.levels.table")}</caption>
          <thead className="border-b border-border text-left">
            <tr>
              {COLUMNS.map((column) => (
                <th key={column} scope="col" className="px-3 py-2 font-medium">
                  {t(`mcp.levels.columns.${column}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((action) => (
              <ActionRow key={`${action.kind}:${action.name}`} action={action} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
