import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { AtsCheckView } from "../viewTypes";
import { checkName } from "./checkName";

interface AtsChecklistProps {
  checks: AtsCheckView[];
}

/**
 * Readability checks by recruitment software: passed or to review, with the detail.
 * The result is written out in full (never by colour alone), and the note reminds
 * that no tool guarantees a pass.
 */
export function AtsChecklist({ checks }: AtsChecklistProps) {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <h3 id={titleId} className="text-sm font-medium">
        {t("cv.ats.title")}
      </h3>
      {checks.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("cv.ats.empty")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {checks.map((check) => (
            <li key={check.id} className="flex flex-col gap-0.5 text-sm">
              <span className="flex flex-wrap items-baseline gap-2">
                <span className="font-medium">{checkName(check.id)}</span>
                <span className="rounded-md border px-1.5 py-0.5 text-xs font-medium">
                  {check.passed ? t("cv.ats.passed") : t("cv.ats.toReview")}
                </span>
              </span>
              <span className="text-muted-foreground">{check.detail}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs text-muted-foreground">{t("cv.ats.guarantee")}</p>
    </section>
  );
}
