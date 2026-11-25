import type { Dispatch, SetStateAction } from "react";
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
  onDraft: Dispatch<SetStateAction<Record<string, string>>>;
  disabled: boolean;
  voice?: boolean;
  onAnswer: (value: unknown) => void;
  optionWithAnswers?: (value: string, answers: Record<string, string>) => unknown;
}

/** What the open card offers: fields, options, or else a free text. */
export function AnswerInputs({
  questionId,
  fields,
  options,
  draft,
  onDraft,
  disabled,
  voice,
  onAnswer,
  optionWithAnswers,
}: AnswerInputsProps) {
  // Answers already typed go with the option (« Lancer la recherche »): never lost.
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
          voice={voice}
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
        <FreeTextAnswer disabled={disabled} onSubmit={onAnswer} voice={voice} />
      ) : null}
    </>
  );
}
