import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import type { InterruptPayload } from "@/shared/realtime/types";
import { FreeTextAnswer } from "../FreeTextAnswer";
import { fieldAnswers } from "./fieldAnswers";
import { InterruptFields } from "./InterruptFields";
import { InterruptOptions } from "./InterruptOptions";

interface InterruptCardProps {
  interrupt: InterruptPayload;
  answered: boolean;
  disabled?: boolean;
  /**
   * Une option envoie sa valeur ; des champs envoient `{ answers: { id: texte } }` (et une option
   * clique après saisie envoie ces réponses, jamais perdues) ; sinon le texte libre.
   */
  onAnswer: (value: unknown) => void;
}

/**
 * Question de l'équipe, affichée comme une carte dans le fil (jamais `window.confirm`).
 * Les options sont des boutons ; sans option ni champ, un champ libre apparaît ; avec des champs
 * (cadrage à plusieurs questions), un champ par question et un bouton « Répondre ». Au clavier :
 * le focus arrive sur la première option (ou sur le premier champ), Tab passe de l'un à l'autre.
 */
export function InterruptCard({
  interrupt,
  answered,
  disabled = false,
  onAnswer,
}: InterruptCardProps) {
  const questionId = useId();
  const locked = answered || disabled;
  const options = interrupt.options ?? [];
  const fields = interrupt.fields ?? [];
  const [draft, setDraft] = useState<Record<string, string>>({});
  // Des réponses déjà saisies partent avec l'option (« Lancer la recherche ») : jamais perdues.
  const pickOption = (value: string) => {
    const answers = fieldAnswers(fields, draft);
    onAnswer(Object.keys(answers).length > 0 ? { answers } : value);
  };

  return (
    <section
      aria-labelledby={questionId}
      className="rounded-xl border-2 border-primary bg-card px-4 py-3 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200"
    >
      <p id={questionId} className="font-medium">
        {interrupt.question}
      </p>
      {fields.length > 0 ? (
        <InterruptFields
          fields={fields}
          draft={draft}
          onDraft={setDraft}
          disabled={locked}
          onSubmit={onAnswer}
        />
      ) : null}
      {options.length > 0 ? (
        <InterruptOptions
          options={options}
          labelledBy={questionId}
          disabled={locked}
          autoFocusFirst={fields.length === 0}
          onPick={pickOption}
        />
      ) : null}
      {options.length === 0 && fields.length === 0 ? (
        <FreeTextAnswer disabled={locked} onSubmit={onAnswer} />
      ) : null}
      {answered ? (
        <p className="mt-2 text-sm text-muted-foreground">{t("session.interrupt.answered")}</p>
      ) : null}
    </section>
  );
}
