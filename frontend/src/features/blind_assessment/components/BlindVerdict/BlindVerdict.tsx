import { t } from "@/shared/i18n/t";
import type { VerdictView } from "../viewTypes";

const winnerText = {
  a: "blindAssessment.winnerA",
  b: "blindAssessment.winnerB",
  tie: "blindAssessment.tie",
} as const;

export function BlindVerdict({ result }: { result: VerdictView }) {
  return (
    <div className="grid gap-3">
      <h4 className="font-semibold">{t("blindAssessment.verdict")}</h4>
      <p role="status">{t(winnerText[result.winner])}</p>
      <p className="whitespace-pre-wrap">{result.feedback}</p>
      <table className="w-full text-left text-sm">
        <caption className="text-left text-muted-foreground">{t("blindAssessment.scoreTable")}</caption>
        <thead>
          <tr>
            <th scope="col" className="py-1">{t("blindAssessment.criterion")}</th>
            <th scope="col" className="px-2">A</th>
            <th scope="col" className="px-2">B</th>
          </tr>
        </thead>
        <tbody>
          {result.scores.map((row) => (
            <tr key={row.label} className="border-t">
              <th scope="row" className="py-1 font-normal">{row.label}</th>
              <td className="px-2">{row.a ?? "—"}</td>
              <td className="px-2">{row.b ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <a className="w-fit underline" href={result.linkA.href}>
        {t("blindAssessment.sourceA", { version: result.linkA.label })}
      </a>
      <a className="w-fit underline" href={result.linkB.href}>
        {t("blindAssessment.sourceB", { version: result.linkB.label })}
      </a>
    </div>
  );
}
