import { useState, type FormEvent, type ReactNode } from "react";
import type { ResponseTiming } from "@/shared/lib/concentration";
import type { LiveQuizPractice } from "@/shared/lib/ghostPanels";
import { t } from "@/shared/i18n/t";
import type { AnswerDraft, QuestionView } from "../viewTypes";
import { QuizQuestions } from "./QuizQuestions";
import { QuizSubmitControls } from "./QuizSubmitControls";
import { useQuizAnswers } from "./useQuizAnswers";
import { useQuizConcentration } from "./useQuizConcentration";
import { useQuizChrono } from "./useQuizChrono";

interface QuizFormProps {
  questions: QuestionView[];
  /** A send is in flight: nothing can be edited any more. */
  disabled: boolean;
  onSubmit: (answers: AnswerDraft[], elapsedMs?: number, timings?: ResponseTiming[]) => void;
  renderGhost?: (live: LiveQuizPractice) => ReactNode;
}

/**
 * The quiz to take: an MCQ as a radio group, code as a text block, open answers as
 * text boxes. « Envoyer » with empty questions asks for confirmation in the card (never
 * `window.confirm`); all answers go out, in question order.
 */
export function QuizForm({ questions, disabled, onSubmit, renderGhost }: QuizFormProps) {
  const { ordered, given, change, empties, drafts } = useQuizAnswers(questions);
  const focus = useQuizConcentration(!disabled);
  const [asking, setAsking] = useState(false);
  const { elapsed, readElapsed } = useQuizChrono(renderGhost !== undefined && !disabled);

  const send = () => {
    if (disabled) return;
    const next = drafts();
    onSubmit(next, readElapsed(), focus.timings(next));
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (empties.length === 0) send();
    else setAsking(true);
  };

  return (
    <form
      onSubmit={submit}
      onPointerDownCapture={focus.activity}
      onKeyDownCapture={focus.activity}
      aria-label={t("quiz.form.label")}
      className="flex flex-col gap-4"
    >
      {renderGhost?.({
        elapsedMs: elapsed,
        answered: ordered.length - empties.length,
        total: ordered.length,
      })}
      <QuizQuestions
        questions={ordered}
        given={given}
        onLeave={focus.leave}
        disabled={disabled}
        onAnswer={(id, patch) => {
          focus.record(id, patch);
          change(id, patch);
          setAsking(false);
        }}
      />
      <QuizSubmitControls
        total={ordered.length}
        empties={empties}
        asking={asking}
        disabled={disabled}
        onSend={send}
        onBack={() => setAsking(false)}
      />
    </form>
  );
}
