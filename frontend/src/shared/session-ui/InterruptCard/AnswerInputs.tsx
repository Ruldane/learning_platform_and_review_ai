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
  optionWithAnswers?: (value: string, answers: Record<string, string>) => unknown;
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
  optionWithAnswers,
}: AnswerInputsProps) {
  // Des réponses déjà saisies partent avec l'option (« Lancer la recherche ») : jamais perdues.
  const pickOption = (value: string) => {
    const answers = fieldAnswers(fields, draft);
    if (Object.keys(answers).length === 0) onAnswer(value);
    else onAnswer(optionWithAnswers ? optionWithAnswers(value, answers) : { answers });
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
