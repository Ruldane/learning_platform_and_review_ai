import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { AnswerDraft, QuestionView } from "../viewTypes";
import { QuestionField } from "./QuestionField";
import { SendConfirm } from "./SendConfirm";
import { useQuizAnswers } from "./useQuizAnswers";

interface QuizFormProps {
  questions: QuestionView[];
  /** Un envoi est en route : plus rien n'est modifiable. */
  disabled: boolean;
  onSubmit: (answers: AnswerDraft[]) => void;
}

/**
 * Le quiz à passer : un QCM en groupe de radios, le code en bloc de texte, les réponses ouvertes en
 * zone de texte. « Envoyer » avec des questions vides demande confirmation dans la carte (jamais
 * `window.confirm`) ; toutes les réponses partent, dans l'ordre des questions.
 */
export function QuizForm({ questions, disabled, onSubmit }: QuizFormProps) {
  const { ordered, given, change, empties, drafts } = useQuizAnswers(questions);
  const [asking, setAsking] = useState(false);

  const send = () => {
    if (!disabled) onSubmit(drafts());
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (empties.length === 0) send();
    else setAsking(true);
  };

  return (
    <form onSubmit={submit} aria-label={t("quiz.form.label")} className="flex flex-col gap-4">
      <ol className="flex flex-col gap-3">
        {ordered.map((question) => (
          <QuestionField
            key={question.id}
            question={question}
            choice={given(question.id).choice}
            text={given(question.id).text}
            disabled={disabled}
            onChoice={(index) => {
              change(question.id, { choice: index });
              setAsking(false);
            }}
            onText={(text) => {
              change(question.id, { text });
              setAsking(false);
            }}
          />
        ))}
      </ol>
      <p className="text-sm text-muted-foreground">
        {t("quiz.form.progress", { done: ordered.length - empties.length, total: ordered.length })}
      </p>
      {asking && empties.length > 0 ? (
        <SendConfirm
          ranks={empties.map((question) => question.rank)}
          disabled={disabled}
          onSend={send}
          onBack={() => setAsking(false)}
        />
      ) : (
        <Button type="submit" className="self-start" disabled={disabled}>
          {t("quiz.form.send")}
        </Button>
      )}
    </form>
  );
}
