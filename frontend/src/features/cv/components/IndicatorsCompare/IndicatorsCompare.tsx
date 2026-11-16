import { t } from "@/shared/i18n/t";
import { CoverageGauge } from "../CoverageGauge";
import type { IndicatorsView } from "../viewTypes";
import { ChecksTable } from "./ChecksTable";

interface IndicatorsCompareProps {
  /** Les indicateurs du CV d'origine. */
  before: IndicatorsView;
  /** Ceux du CV généré, ou `null` tant qu'il n'existe pas. */
  after: IndicatorsView | null;
}

/**
 * Les deux indicateurs du CV avant et après : la couverture des exigences en jauge, ce qui reste à
 * couvrir, et les contrôles de lisibilité en tableau.
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
