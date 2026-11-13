import { useEffect, useRef } from "react";
import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button, buttonVariants } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { QuizResult } from "../../components/QuizResult";
import { useAttempt } from "../../hooks/useAttempt";
import { toAttemptResultView } from "../../toView";
import { GradingFailed } from "./GradingFailed";
import { GradingLate } from "./GradingLate";
import type { TakenAttempt } from "./takenAttempt";

interface AttemptPanelProps {
  quizId: string;
  taken: TakenAttempt;
  /** Le quiz est relu : « Refaire le quiz » attend l'ordre du prochain essai. */
  refreshing: boolean;
  /** Message d'un renvoi refusé. */
  error: string | null;
  gradePollMs: number;
  onResend: () => void;
  onBack: () => void;
}

/**
 * Après l'envoi : la note se prépare (relue toutes les 2 s, 90 fois), puis le résultat ; une note
 * échouée propose de renvoyer les réponses ; une note trop longue propose de la relire.
 */
export function AttemptPanel(props: AttemptPanelProps) {
  const { quizId, taken, refreshing, error, gradePollMs, onResend, onBack } = props;
  const { query, budget } = useAttempt(quizId, taken.attemptId, gradePollMs);
  const result = useRef<HTMLDivElement>(null);
  const attempt = query.data;
  const graded = attempt?.status === "graded";
  // Le résultat arrive à la place du formulaire : le focus y va pour que la note soit lue.
  useEffect(() => {
    if (graded) result.current?.focus();
  }, [graded]);

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
        onResend={onResend}
        onBack={onBack}
      />
    );
  }
  return (
    <div ref={result} tabIndex={-1} className="flex flex-col gap-4 outline-none">
      <QuizResult result={toAttemptResultView(attempt, taken.questions)} />
      <div className="flex flex-wrap gap-2">
        <Button disabled={refreshing} onClick={onBack}>
          {t("quiz.page.again")}
        </Button>
        <Link to="/etudier/quiz" className={buttonVariants({ variant: "outline" })}>
          {t("quiz.page.allQuizzes")}
        </Link>
      </div>
    </div>
  );
}
