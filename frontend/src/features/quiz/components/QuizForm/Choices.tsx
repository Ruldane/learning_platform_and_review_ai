import { useId } from "react";
import type { QuestionView } from "../viewTypes";

interface ChoicesProps {
  question: QuestionView;
  choice: number | null;
  disabled: boolean;
  /** `id` de l'énoncé, qui nomme le groupe. */
  labelledBy: string;
  onChoice: (index: number) => void;
}

/** Les choix d'un QCM : un groupe de radios, une seule réponse. */
export function Choices({ question, choice, disabled, labelledBy, onChoice }: ChoicesProps) {
  const name = useId();
  return (
    <div role="radiogroup" aria-labelledby={labelledBy} className="mt-2 flex flex-col gap-1.5">
      {question.choices.map((label, index) => (
        <label
          key={index}
          className="flex cursor-pointer items-start gap-2 rounded-lg border px-3 py-2 text-sm has-[:checked]:border-primary has-[:checked]:bg-muted"
        >
          <input
            type="radio"
            name={name}
            checked={choice === index}
            disabled={disabled}
            onChange={() => onChoice(index)}
            className="mt-0.5"
          />
          <span>{label}</span>
        </label>
      ))}
    </div>
  );
}
