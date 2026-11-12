import { Check, Minus, X } from "lucide-react";
import { t } from "@/shared/i18n/t";
import type { QuestionResultView } from "../viewTypes";
import { Explanations } from "./Explanations";
import { formatPoints } from "./points";

type Verdict = "ok" | "partial" | "fail";

function verdictOf(points: number): Verdict {
  if (points >= 1) return "ok";
  return points > 0 ? "partial" : "fail";
}

const VERDICT_STYLE = {
  ok: { Icon: Check, className: "text-primary" },
  partial: { Icon: Minus, className: "text-amber-900" },
  fail: { Icon: X, className: "text-destructive" },
} as const;

/**
 * Une question corrigée. Une erreur (même partielle) montre tout de suite la bonne réponse, son
 * explication et le retour ; une réponse juste les garde à un clic, dans un bloc replié.
 */
export function QuestionResult({ result }: { result: QuestionResultView }) {
  const verdict = verdictOf(result.points);
  const { Icon, className } = VERDICT_STYLE[verdict];
  return (
    <li className="rounded-xl border bg-card p-4">
      <p className="flex flex-wrap items-center gap-x-2 text-sm">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {t("quiz.result.question", { rank: result.rank })}
        </span>
        <span className={`inline-flex items-center gap-1 font-medium ${className}`}>
          <Icon aria-hidden="true" className="size-4" />
          {t(`quiz.result.verdict.${verdict}`)}
        </span>
        <span className="text-muted-foreground tabular-nums">
          {t("quiz.result.point", { points: formatPoints(result.points) })}
        </span>
      </p>
      <p className="mt-1 whitespace-pre-wrap font-medium">{result.prompt}</p>
      {verdict === "ok" ? (
        <details className="mt-2">
          <summary className="cursor-pointer text-sm text-primary">
            {t("quiz.result.details")}
          </summary>
          <Explanations result={result} />
        </details>
      ) : (
        <Explanations result={result} />
      )}
    </li>
  );
}
