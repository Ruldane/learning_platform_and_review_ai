import { t } from "@/shared/i18n/t";
import { IndicatorsCompare } from "../../components/IndicatorsCompare";
import { latestVersion, toIndicatorsView } from "../../toView";
import type { CvReviewOut } from "../../types";
import { Section } from "./Section";

/** The indicators of the original CV, and those of the latest ready version if one exists. */
export function IndicatorsSection({ review }: { review: CvReviewOut }) {
  const latest = latestVersion(review);
  return (
    <Section title={t("cv.reviewPage.indicators")}>
      {review.before ? (
        <IndicatorsCompare
          before={toIndicatorsView(review.before)}
          after={latest?.indicators ? toIndicatorsView(latest.indicators) : null}
        />
      ) : (
        <p className="text-sm text-muted-foreground">{t("cv.reviewPage.noIndicators")}</p>
      )}
    </Section>
  );
}
