import type { InterruptPayload } from "@/shared/realtime/types";
import { FreeTextAnswer } from "../FreeTextAnswer";
import { fieldAnswers, type InterruptField } from "./fieldAnswers";
import { InterruptFields } from "./InterruptFields";
import { InterruptOptions } from "./InterruptOptions";

interface AnswerInputsProps {
  questionId: string;
  fields: InterruptField[];
  options: NonNullable<InterruptPayload["options"]>;
  draft: Record<string, string>;
  onDraft: (draft: Record<string, string>) => void;
  disabled: boolean;
  onAnswer: (value: unknown) => void;
}

/** Ce que la carte ouverte propose : des champs, des options, ou à défaut un texte libre. */
export function AnswerInputs({
  questionId,
  fields,
  options,
  draft,
  onDraft,
  disabled,
  onAnswer,
}: AnswerInputsProps) {
  // Des réponses déjà saisies partent avec l'option (« Lancer la recherche ») : jamais perdues.
  const pickOption = (value: string) => {
    const answers = fieldAnswers(fields, draft);
    onAnswer(Object.keys(answers).length > 0 ? { answers } : value);
  };
  return (
    <>
      {fields.length > 0 ? (
        <InterruptFields
          fields={fields}
          draft={draft}
          onDraft={onDraft}
          disabled={disabled}
          onSubmit={onAnswer}
        />
      ) : null}
      {options.length > 0 ? (
        <InterruptOptions
          options={options}
          labelledBy={questionId}
          disabled={disabled}
          autoFocusFirst={fields.length === 0}
          onPick={pickOption}
        />
      ) : null}
      {options.length === 0 && fields.length === 0 ? (
        <FreeTextAnswer disabled={disabled} onSubmit={onAnswer} />
      ) : null}
    </>
  );
}
