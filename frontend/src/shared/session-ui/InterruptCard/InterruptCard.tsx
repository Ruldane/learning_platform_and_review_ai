import { useId, useState } from "react";
import type { InterruptPayload } from "@/shared/realtime/types";
import { AnswerInputs } from "./AnswerInputs";
import { FoldedCard } from "./FoldedCard";

const cardClass =
  "rounded-xl border-2 border-primary bg-card px-4 py-3 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200";

interface InterruptCardProps {
  interrupt: InterruptPayload;
  answered: boolean;
  disabled?: boolean;
  /**
   * Une option envoie sa valeur ; des champs envoient `{ answers: { id: texte } }` (et une option
   * clique après saisie envoie ces réponses, jamais perdues) ; sinon le texte libre.
   */
  onAnswer: (value: unknown) => void;
  /**
   * Valeur envoyée quand une option est cliquée alors que des champs sont remplis ; par défaut
   * `{ answers }`. Sert quand l'option doit garder le dessus (« Accepter » avec une note).
   */
  optionWithAnswers?: (value: string, answers: Record<string, string>) => unknown;
}

/**
 * Question de l'équipe, affichée comme une carte dans le fil (jamais `window.confirm`). Les
 * options sont des boutons ; sans option ni champ, un champ libre apparaît ; avec des champs
 * (cadrage à plusieurs questions), un champ par question et un bouton « Répondre ». Au clavier :
 * le focus arrive sur la première option (ou sur le premier champ), Tab passe de l'un à l'autre.
 * Une fois répondue, la carte se replie : la question, « Réponse envoyée » et les réponses saisies
 * dans cet onglet en lecture seule, sans plus aucun champ, option ni texte libre.
 */
export function InterruptCard({
  interrupt,
  answered,
  disabled = false,
  onAnswer,
  optionWithAnswers,
}: InterruptCardProps) {
  const questionId = useId();
  const fields = interrupt.fields ?? [];
  const [draft, setDraft] = useState<Record<string, string>>({});

  if (answered) {
    return (
      <FoldedCard
        questionId={questionId}
        question={interrupt.question}
        className={cardClass}
        fields={fields}
        draft={draft}
      />
    );
  }
  return (
    <section aria-labelledby={questionId} className={cardClass}>
      <p id={questionId} className="font-medium">
        {interrupt.question}
      </p>
      <AnswerInputs
        questionId={questionId}
        fields={fields}
        options={interrupt.options ?? []}
        draft={draft}
        onDraft={setDraft}
        disabled={disabled}
        onAnswer={onAnswer}
        optionWithAnswers={optionWithAnswers}
      />
    </section>
  );
}
