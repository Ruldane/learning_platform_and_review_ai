import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { QuestionView } from "../viewTypes";
import { Choices } from "./Choices";
import { CodeBlock } from "./CodeBlock";
import { OpenAnswer } from "./OpenAnswer";

interface QuestionFieldProps {
  question: QuestionView;
  choice: number | null;
  text: string;
  disabled: boolean;
  onChoice: (index: number) => void;
  onText: (text: string) => void;
}

/**
 * Une question du quiz : son type et sa consigne, l'énoncé, le code éventuel (affiché tel quel,
 * jamais interprété) puis les choix d'un QCM ou la zone de réponse des autres types.
 */
export function QuestionField({
  question,
  choice,
  text,
  disabled,
  onChoice,
  onText,
}: QuestionFieldProps) {
  const promptId = useId();
  const { rank, type } = question;
  return (
    <li data-question={question.id} className="rounded-xl border bg-card p-4">
      <p className="text-xs text-muted-foreground">
        <span className="font-medium uppercase tracking-wide">
          {t("quiz.form.question", { rank })}
        </span>
        {" · "}
        <span className="font-medium">{t(`quiz.form.type.${type}`)}</span>
        {" · "}
        <span>{t(`quiz.form.hint.${type}`)}</span>
      </p>
      <p id={promptId} className="mt-1 whitespace-pre-wrap font-medium">
        {question.prompt}
      </p>
      {question.code !== null ? <CodeBlock rank={rank} code={question.code} /> : null}
      {type === "qcm" ? (
        <Choices
          question={question}
          choice={choice}
          disabled={disabled}
          labelledBy={promptId}
          onChoice={onChoice}
        />
      ) : (
        <OpenAnswer
          rank={rank}
          rows={type === "short" ? 2 : 4}
          text={text}
          disabled={disabled}
          onText={onText}
        />
      )}
    </li>
  );
}
