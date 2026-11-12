import { t } from "@/shared/i18n/t";
import type { QuestionResultView } from "../viewTypes";

/** Bonne réponse, explication et retour d'une question : chaque partie vide est omise. */
export function Explanations({ result }: { result: QuestionResultView }) {
  const parts = [
    { label: t("quiz.result.correct"), text: result.correctAnswer },
    { label: t("quiz.result.explanation"), text: result.explanation },
    { label: t("quiz.result.feedback"), text: result.feedback },
  ].filter((part) => part.text !== "");
  return (
    <dl className="mt-2 flex flex-col gap-2">
      {parts.map((part) => (
        <div key={part.label}>
          <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {part.label}
          </dt>
          <dd className="whitespace-pre-wrap text-sm">{part.text}</dd>
        </div>
      ))}
    </dl>
  );
}
