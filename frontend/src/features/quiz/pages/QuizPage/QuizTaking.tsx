import { useMemo, useState } from "react";
import type { AnswerDraft, QuestionView } from "../../components/viewTypes";
import { useSubmitAttempt } from "../../hooks/useSubmitAttempt";
import { pendingRetryOn, toQuestionViews } from "../../toView";
import type { QuizOut } from "../../types";
import { AttemptPanel } from "./AttemptPanel";
import { QuizEntry } from "./QuizEntry";
import type { TakenAttempt } from "./takenAttempt";

interface QuizTakingProps {
  quiz: QuizOut;
  /** Le quiz est en cours de relecture (après une note) : l'ordre des questions peut changer. */
  refreshing: boolean;
  gradePollMs: number;
}

/** Une correction déjà en cours (page rechargée) est reprise : l'ordre affiché n'a pas changé depuis. */
function resumeGrading(quiz: QuizOut): TakenAttempt | null {
  const grading = quiz.attempts.find((attempt) => attempt.status === "grading");
  return grading
    ? { attemptId: grading.id, questions: toQuestionViews(quiz.questions), drafts: null }
    : null;
}

/**
 * Un quiz prêt : le formulaire, puis, une fois les réponses envoyées, la note et le résultat. Les
 * questions jointes au résultat sont celles de l'envoi : le quiz relu après la note, lui, montre
 * déjà l'ordre du prochain essai (F27). Après un échec, tant que la date du nouvel essai n'est pas
 * venue, la date remplace le formulaire (le back refuserait l'envoi : 409 `retry_too_soon`).
 */
export function QuizTaking({ quiz, refreshing, gradePollMs }: QuizTakingProps) {
  const submitter = useSubmitAttempt(quiz.id);
  const [round, setRound] = useState(0);
  const [taken, setTaken] = useState<TakenAttempt | null>(() => resumeGrading(quiz));
  const questions = useMemo(() => toQuestionViews(quiz.questions), [quiz.questions]);

  const send = async (drafts: AnswerDraft[], shown: QuestionView[] = questions) => {
    const attemptId = await submitter.submit(drafts);
    if (attemptId) setTaken({ attemptId, questions: shown, drafts });
  };
  const back = () => {
    submitter.release();
    setRound((count) => count + 1);
    setTaken(null);
  };
  const resend = () => {
    if (!taken?.drafts) return;
    submitter.release();
    void send(taken.drafts, taken.questions);
  };

  if (taken) {
    return (
      <AttemptPanel
        key={taken.attemptId}
        quizId={quiz.id}
        taken={taken}
        refreshing={refreshing}
        error={submitter.error}
        sending={submitter.pending}
        gradePollMs={gradePollMs}
        onResend={resend}
        onBack={back}
      />
    );
  }
  return (
    <QuizEntry
      attempts={quiz.attempts}
      questions={questions}
      retryOn={pendingRetryOn(quiz.attempts)}
      error={submitter.error}
      pending={submitter.pending}
      round={round}
      onSubmit={(drafts) => void send(drafts)}
    />
  );
}
