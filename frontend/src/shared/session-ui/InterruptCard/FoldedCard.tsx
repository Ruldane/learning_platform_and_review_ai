import { t } from "@/shared/i18n/t";
import { fieldAnswers, type InterruptField } from "./fieldAnswers";

interface FoldedCardProps {
  questionId: string;
  question: string;
  className: string;
  fields: InterruptField[];
  /** What was typed in this tab; empty when the answer came from elsewhere (other tab, reload). */
  draft: Record<string, string>;
}

/**
 * Answered card, folded: the question, « Réponse envoyée » and the answers typed in this
 * tab (field label and text sent), read-only. No more fields, options or free text;
 * fields left empty are omitted.
 */
export function FoldedCard({ questionId, question, className, fields, draft }: FoldedCardProps) {
  const answers = fieldAnswers(fields, draft);
  const given = fields.filter((field) => answers[field.id] !== undefined);
  return (
    <section aria-labelledby={questionId} className={className}>
      <p id={questionId} className="font-medium">
        {question}
      </p>
      {given.length > 0 ? (
        <dl className="mt-2 flex flex-col gap-2 text-sm">
          {given.map((field) => (
            <div key={field.id} className="flex flex-col gap-0.5">
              <dt className="text-muted-foreground">{field.label}</dt>
              <dd className="whitespace-pre-wrap">{answers[field.id]}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      <p className="mt-2 text-sm text-muted-foreground">{t("session.interrupt.answered")}</p>
    </section>
  );
}
