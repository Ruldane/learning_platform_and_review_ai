import { t } from "@/shared/i18n/t";
import type { ResultView } from "../viewTypes";

const assessedFormat = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeStyle: "short" });

export function TransferResult({ assessment }: { assessment: ResultView }) {
  return (
    <div className="grid gap-2">
      <h4 role="status" className="font-semibold">
        {t(
          assessment.demonstrated
            ? "skillTransfer.demonstrated"
            : "skillTransfer.needsReview",
        )}
      </h4>
      <time dateTime={assessment.date} className="text-sm text-muted-foreground">
        {t("skillTransfer.assessed", { date: assessedFormat.format(new Date(assessment.date)) })}
      </time>
      <p className="whitespace-pre-wrap">{assessment.feedback}</p>
      <ul className="list-disc space-y-1 pl-5">
        {assessment.criteria.map((criterion) => (
          <li key={criterion.text}>
            {criterion.text} · {t(criterion.demonstrated ? "skillTransfer.met" : "skillTransfer.missed")}
          </li>
        ))}
      </ul>
    </div>
  );
}
