import { t } from "@/shared/i18n/t";
import type { FeynmanReport } from "../../feynmanApi";

export function ExplanationTranscript({ report }: { report: FeynmanReport }) {
  return (
    <details className="rounded-md border border-border p-2">
      <summary className="cursor-pointer">{t("feynman.transcript")}</summary>
      <p className="whitespace-pre-wrap">{report.explanation}</p>
      {report.follow_up && <p className="font-medium">{report.follow_up}</p>}
      {report.clarification && <p className="whitespace-pre-wrap">{report.clarification}</p>}
    </details>
  );
}
