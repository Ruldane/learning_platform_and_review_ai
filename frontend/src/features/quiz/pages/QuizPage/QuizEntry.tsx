import { t } from "@/shared/i18n/t";
import { longDay } from "@/shared/lib/format";
import { InlineError } from "@/shared/ui/states/InlineError";
import { QuizForm } from "../../components/QuizForm";
import type { AnswerDraft, QuestionView } from "../../components/viewTypes";
import type { AttemptSummaryOut } from "../../types";
import { AttemptHistory } from "./AttemptHistory";

interface QuizEntryProps {
  attempts: AttemptSummaryOut[];
  questions: QuestionView[];
  /** Jour du nouvel essai encore à venir : il remplace le formulaire ; `null` sinon. */
  retryOn: string | null;
  /** Message d'un envoi refusé. */
  error: string | null;
  pending: boolean;
  /** Change à chaque retour au formulaire : il repart vide. */
  round: number;
  onSubmit: (drafts: AnswerDraft[]) => void;
}

/** Avant l'envoi : les essais précédents, puis le formulaire, ou la date du nouvel essai (F9). */
export function QuizEntry(props: QuizEntryProps) {
  const { attempts, questions, retryOn, error, pending, round, onSubmit } = props;
  return (
    <>
      <AttemptHistory attempts={attempts} />
      {error ? <InlineError message={error} /> : null}
      {retryOn !== null ? (
        <p role="status" className="rounded-xl border bg-card p-4 text-sm">
          {t("quiz.page.retryTooSoon", { date: longDay(retryOn) })}
        </p>
      ) : (
        <QuizForm key={round} questions={questions} disabled={pending} onSubmit={onSubmit} />
      )}
    </>
  );
}
