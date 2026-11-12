import { t } from "@/shared/i18n/t";
import { fieldAnswers, type InterruptField } from "./fieldAnswers";

interface FoldedCardProps {
  questionId: string;
  question: string;
  className: string;
  fields: InterruptField[];
  /** Ce qui a été saisi dans cet onglet ; vide quand la réponse vient d'ailleurs (autre onglet, rechargement). */
  draft: Record<string, string>;
}

/**
 * Carte répondue, repliée : la question, « Réponse envoyée » et les réponses saisies dans cet
 * onglet (étiquette du champ et texte envoyé), en lecture seule. Plus aucun champ, option ni texte
 * libre ; les champs laissés vides sont omis.
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
