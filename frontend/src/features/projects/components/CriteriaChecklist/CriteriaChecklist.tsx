import { t } from "@/shared/i18n/t";
import type { CriterionResultView } from "../viewTypes";
import { Mark } from "./Mark";

interface CriteriaChecklistProps {
  criteria: string[];
  /** The evaluation results (index from 1); `null` before any evaluation. */
  results: CriterionResultView[] | null;
}

/** Project criteria, each marked « Atteint » or « Non atteint », with the Practitioner's note. */
export function CriteriaChecklist({ criteria, results }: CriteriaChecklistProps) {
  return (
    <ol aria-label={t("projects.criteria.label")} className="flex flex-col gap-3">
      {criteria.map((criterion, position) => {
        const result = results?.find((item) => item.index === position + 1) ?? null;
        const label = result
          ? result.met
            ? t("projects.criteria.met")
            : t("projects.criteria.notMet")
          : t("projects.criteria.pending");
        return (
          <li key={`${position}-${criterion}`} className="flex gap-2 text-sm">
            <Mark met={result ? result.met : null} />
            <div className="flex flex-col gap-0.5">
              <span>{criterion}</span>
              <span className="font-medium">{label}</span>
              {result?.comment ? (
                <span className="text-muted-foreground">{result.comment}</span>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
