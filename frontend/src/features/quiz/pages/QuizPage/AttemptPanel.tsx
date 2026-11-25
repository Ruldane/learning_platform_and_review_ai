import type { ComponentType } from "react";
import type { QuizGhostProps } from "@/shared/lib/ghostPanels";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useAttempt } from "../../hooks/useAttempt";
import { toAttemptResultView } from "../../toView";
import { TimedAttemptResult } from "./TimedAttemptResult";
import { GradingFailed } from "./GradingFailed";
import { GradingLate } from "./GradingLate";
import type { TakenAttempt } from "./takenAttempt";

interface AttemptPanelProps {
  quizId: string;
  taken: TakenAttempt;
  /** The quiz is re-read: « Refaire le quiz » waits for the next attempt's order. */
  refreshing: boolean;
  /** Message for a refused resend. */
  error: string | null;
  /** A resend is in flight: « Renvoyer mes réponses » is off. */
  sending: boolean;
  gradePollMs: number;
  onResend: () => void;
  onBack: () => void;
  GhostPanel?: ComponentType<QuizGhostProps>;
}

/**
 * After sending: the grade is prepared (re-read every 2 s, 90 times), then the result.
 * A failed grade offers to resend the answers; a grade that takes too long offers a re-read.
 * After a failure, « Refaire le quiz » only appears once the new attempt's date has come (F9).
 */
export function AttemptPanel(props: AttemptPanelProps) {
  const { quizId, taken, refreshing, error, sending, gradePollMs, onResend, onBack, GhostPanel } =
    props;
  const { query, budget } = useAttempt(quizId, taken.attemptId, gradePollMs);
  const attempt = query.data;

  if (query.isError) {
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  if (!attempt || (attempt.status === "grading" && !budget.exhausted)) {
    return <LoadingState label={t("quiz.page.grading")} />;
  }
  if (attempt.status === "grading") {
    return (
      <GradingLate
        onKeepWaiting={() => {
          budget.restart();
          void query.refetch();
        }}
      />
    );
  }
  if (attempt.status === "failed") {
    return (
      <GradingFailed
        canResend={taken.drafts !== null}
        error={error}
        sending={sending}
        onResend={onResend}
        onBack={onBack}
      />
    );
  }
  return (
    <TimedAttemptResult
      result={toAttemptResultView(attempt, taken.questions)}
      timings={taken.timings}
      refreshing={refreshing}
      onBack={onBack}
    >
      {GhostPanel && <GhostPanel quizId={quizId} currentAttemptId={attempt.id} />}
    </TimedAttemptResult>
  );
}
