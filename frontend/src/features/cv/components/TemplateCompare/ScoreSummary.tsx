import { t } from "@/shared/i18n/t";
import type { ZoneView } from "../viewTypes";
import { zoneSentences } from "./zoneSentences";

interface ScoreSummaryProps {
  score: number | null;
  zones: ZoneView[];
  passes: number;
}

function passesText(passes: number): string {
  if (passes <= 0) return t("cv.template.passes.none");
  return passes === 1
    ? t("cv.template.passes.one")
    : t("cv.template.passes.many", { count: passes });
}

/** « Ressemblance : 87 % », le nombre d'ajustements, et les zones qui diffèrent en phrases. */
export function ScoreSummary({ score, zones, passes }: ScoreSummaryProps) {
  const sentences = zoneSentences(zones);
  return (
    <div className="flex flex-col gap-1">
      <p className="text-lg font-semibold tabular-nums">
        {score === null
          ? t("cv.template.similarityNone")
          : t("cv.template.similarity", { score: Math.min(100, Math.max(0, Math.round(score))) })}
      </p>
      <p className="text-sm text-muted-foreground">{passesText(passes)}</p>
      {score === null ? null : (
        <>
          <h3 className="mt-1 text-sm font-medium">{t("cv.template.zones")}</h3>
          {sentences.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("cv.template.zonesNone")}</p>
          ) : (
            <ul className="list-disc pl-5 text-sm">
              {sentences.map((sentence) => (
                <li key={sentence}>{sentence}</li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
