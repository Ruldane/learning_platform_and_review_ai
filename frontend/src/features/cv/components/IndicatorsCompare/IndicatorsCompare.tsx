import { t } from "@/shared/i18n/t";
import { CoverageGauge } from "../CoverageGauge";
import type { IndicatorsView } from "../viewTypes";
import { ChecksTable } from "./ChecksTable";

interface IndicatorsCompareProps {
  /** The indicators of the original CV. */
  before: IndicatorsView;
  /** Those of the generated CV, or `null` until it exists. */
  after: IndicatorsView | null;
}

/**
 * The two indicators of the CV before and after: the coverage of requirements as a gauge,
 * what remains to cover, and the readability checks as a table.
 */
export function IndicatorsCompare({ before, after }: IndicatorsCompareProps) {
  const missing = (after ?? before).missing;
  return (
    <div className="flex flex-col gap-4">
      <CoverageGauge before={before.coveragePercent} after={after?.coveragePercent ?? null} />
      {missing.length > 0 ? (
        <section className="flex flex-col gap-1">
          <h4 className="text-sm font-medium">{t("cv.indicators.missing")}</h4>
          <ul className="flex flex-wrap gap-1.5">
            {missing.map((term, index) => (
              <li key={index} className="rounded-md bg-muted px-2 py-0.5 text-sm">
                {term}
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <p className="text-sm text-muted-foreground">{t("cv.indicators.allCovered")}</p>
      )}
      <ChecksTable before={before} after={after} />
      <p className="text-xs text-muted-foreground">{t("cv.ats.guarantee")}</p>
    </div>
  );
}
