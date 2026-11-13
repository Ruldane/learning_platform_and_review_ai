import { t } from "@/shared/i18n/t";
import { checkName } from "../AtsChecklist";
import type { AtsCheckView, IndicatorsView } from "../viewTypes";

interface ChecksTableProps {
  before: IndicatorsView;
  after: IndicatorsView | null;
}

const verdict = (check: AtsCheckView | undefined): string => {
  if (check === undefined) return t("cv.indicators.unknown");
  return check.passed ? t("cv.ats.passed") : t("cv.ats.toReview");
};

/** Chaque contrôle de lisibilité, avant et après, écrit en toutes lettres. */
export function ChecksTable({ before, after }: ChecksTableProps) {
  const ids = [...new Set([...before.checks, ...(after?.checks ?? [])].map((check) => check.id))];
  return (
    <div className="overflow-x-auto rounded-xl border bg-card">
      <table aria-label={t("cv.ats.title")} className="w-full text-sm">
        <thead>
          <tr className="border-b text-left">
            <th scope="col" className="px-3 py-2 font-medium">
              {t("cv.indicators.check")}
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              {t("cv.indicators.before")}
            </th>
            <th scope="col" className="px-3 py-2 font-medium">
              {t("cv.indicators.after")}
            </th>
          </tr>
        </thead>
        <tbody>
          {ids.map((id) => (
            <tr key={id} className="border-b last:border-0">
              <th scope="row" className="px-3 py-2 text-left font-normal">
                {checkName(id)}
              </th>
              <td className="px-3 py-2">{verdict(before.checks.find((c) => c.id === id))}</td>
              <td className="px-3 py-2">
                {after === null
                  ? t("cv.indicators.noAfter")
                  : verdict(after.checks.find((c) => c.id === id))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
