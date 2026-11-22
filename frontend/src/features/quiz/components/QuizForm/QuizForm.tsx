import { useState, type FormEvent, type ReactNode } from "react";
import type { LiveQuizPractice } from "@/shared/lib/ghostPanels";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { AnswerDraft, QuestionView } from "../viewTypes";
import { QuizQuestions } from "./QuizQuestions";
import { SendConfirm } from "./SendConfirm";
import { useQuizAnswers } from "./useQuizAnswers";
import { useQuizChrono } from "./useQuizChrono";

interface QuizFormProps {
  questions: QuestionView[];
  /** Un envoi est en route : plus rien n'est modifiable. */
  disabled: boolean;
  onSubmit: (answers: AnswerDraft[], elapsedMs?: number) => void;
  renderGhost?: (live: LiveQuizPractice) => ReactNode;
}

/**
 * Le quiz à passer : un QCM en groupe de radios, le code en bloc de texte, les réponses ouvertes en
 * zone de texte. « Envoyer » avec des questions vides demande confirmation dans la carte (jamais
 * `window.confirm`) ; toutes les réponses partent, dans l'ordre des questions.
 */
export function QuizForm({ questions, disabled, onSubmit, renderGhost }: QuizFormProps) {
  const { ordered, given, change, empties, drafts } = useQuizAnswers(questions);
  const [asking, setAsking] = useState(false);
  const { elapsed, readElapsed } = useQuizChrono(renderGhost !== undefined && !disabled);

  const send = () => {
    if (!disabled) onSubmit(drafts(), readElapsed());
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (empties.length === 0) send();
    else setAsking(true);
  };

  return (
    <form onSubmit={submit} aria-label={t("quiz.form.label")} className="flex flex-col gap-4">
      {renderGhost?.({
        elapsedMs: elapsed,
        answered: ordered.length - empties.length,
        total: ordered.length,
      })}
      <QuizQuestions
        questions={ordered}
        given={given}
        disabled={disabled}
        onAnswer={(id, patch) => {
          change(id, patch);
          setAsking(false);
        }}
      />
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
