import type { QuizGhostProps } from "@/shared/lib/ghostPanels";
import { useMemo, useState, type ComponentType } from "react";
import type { AnswerDraft } from "../../components/viewTypes";
import { useSubmitAttempt } from "../../hooks/useSubmitAttempt";
import { pendingRetryOn, toQuestionViews } from "../../toView";
import type { QuizOut } from "../../types";
import { AttemptPanel } from "./AttemptPanel";
import { QuizEntry } from "./QuizEntry";
import type { TakenAttempt } from "./takenAttempt";

type Presented = Omit<TakenAttempt, "attemptId" | "drafts">;

interface QuizTakingProps {
  quiz: QuizOut;
  /** The quiz is being re-read (after a grade): the question order may change. */
  refreshing: boolean;
  gradePollMs: number;
  GhostPanel?: ComponentType<QuizGhostProps>;
}

/** A grading already running (page reloaded) is resumed: the order shown has not changed since. */
function resumeGrading(quiz: QuizOut): TakenAttempt | null {
  const grading = quiz.attempts.find((attempt) => attempt.status === "grading");
  return grading
    ? { attemptId: grading.id, questions: toQuestionViews(quiz.questions), drafts: null }
    : null;
}

/**
 * A ready quiz: the form, then, once the answers are sent, the grade and the result. The
 * questions attached to the result are those of the send: the quiz re-read after the grade already
 * shows the next attempt's order (F27). After a failure, until the new attempt's date has come,
 * the date replaces the form (the back end would refuse the send: 409 `retry_too_soon`).
 */
export function QuizTaking({ quiz, refreshing, gradePollMs, GhostPanel }: QuizTakingProps) {
  const submitter = useSubmitAttempt(quiz.id);
  const [round, setRound] = useState(0);
  const [taken, setTaken] = useState<TakenAttempt | null>(() => resumeGrading(quiz));
  const questions = useMemo(() => toQuestionViews(quiz.questions), [quiz.questions]);

  const send = async (drafts: AnswerDraft[], presentation: Presented) => {
    const attemptId = await submitter.submit(drafts, presentation.elapsedMs);
    if (attemptId) setTaken({ ...presentation, attemptId, drafts });
  };
  const back = () => {
    submitter.release();
    setRound((count) => count + 1);
    setTaken(null);
  };
  const resend = () => {
    if (!taken?.drafts) return;
    submitter.release();
    void send(taken.drafts, taken);
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
        GhostPanel={GhostPanel}
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
      onSubmit={(drafts, elapsedMs, timings) =>
        void send(drafts, { questions, elapsedMs, timings })
      }
      renderGhost={GhostPanel ? (live) => <GhostPanel quizId={quiz.id} live={live} /> : undefined}
    />
  );
}
