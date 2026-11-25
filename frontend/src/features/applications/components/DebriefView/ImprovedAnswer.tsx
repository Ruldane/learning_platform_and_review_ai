import { t } from "@/shared/i18n/t";
import type { ExchangeView } from "../viewTypes";

interface ImprovedAnswerProps {
  text: string;
  /** The terms the profile does not state: the answer is then « à vérifier ». */
  flags: string[];
  /** The weakest question, which the answer addresses. */
  question: ExchangeView | undefined;
}

/** The improved answer to the weakest question; « à vérifier » with its terms when the profile does
 * not state them. */
export function ImprovedAnswer({ text, flags, question }: ImprovedAnswerProps) {
  const toCheck = flags.length > 0;
  return (
    <section className="flex flex-col gap-2">
      <h3 className="flex flex-wrap items-center gap-2 text-lg font-semibold">
        {t("applications.debrief.improved")}
        {toCheck ? (
          <span className="rounded-md border px-2 py-0.5 text-xs font-medium">
            {t("applications.debrief.toCheck")}
          </span>
        ) : null}
      </h3>
      {question ? (
        <p className="text-sm text-muted-foreground">
          {t("applications.debrief.improvedFor", {
            number: question.index + 1,
            question: question.question,
          })}
        </p>
      ) : null}
      <p className="max-w-prose whitespace-pre-wrap">{text}</p>
      {toCheck ? (
        <p role="note" className="max-w-prose text-sm">
          {t("applications.debrief.toCheckTerms", { terms: flags.join(", ") })}
        </p>
      ) : null}
    </section>
  );
}
