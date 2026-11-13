import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useAttempt } from "../../hooks/useAttempt";
import { toAttemptResultView } from "../../toView";
import { AttemptResult } from "./AttemptResult";
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
  /** Un renvoi est en route : « Renvoyer mes réponses » est coupé. */
  sending: boolean;
  gradePollMs: number;
  onResend: () => void;
  onBack: () => void;
}

/**
 * Après l'envoi : la note se prépare (relue toutes les 2 s, 90 fois), puis le résultat ; une note
 * échouée propose de renvoyer les réponses ; une note trop longue propose de la relire. Après un
 * échec, « Refaire le quiz » n'apparaît qu'une fois la date du nouvel essai venue (F9).
 */
export function AttemptPanel(props: AttemptPanelProps) {
  const { quizId, taken, refreshing, error, sending, gradePollMs, onResend, onBack } = props;
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
    <AttemptResult
      result={toAttemptResultView(attempt, taken.questions)}
      refreshing={refreshing}
      onBack={onBack}
    />
  );
}
