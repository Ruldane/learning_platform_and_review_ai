import type { ReactNode } from "react";
import type { ResponseTiming } from "@/shared/lib/concentration";
import type { LiveQuizPractice } from "@/shared/lib/ghostPanels";
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
  /** Day of the new attempt still to come: it replaces the form; `null` otherwise. */
  retryOn: string | null;
  /** Message for a refused send. */
  error: string | null;
  pending: boolean;
  /** Changes on each return to the form: it starts empty. */
  round: number;
  onSubmit: (drafts: AnswerDraft[], elapsedMs?: number, timings?: ResponseTiming[]) => void;
  renderGhost?: (live?: LiveQuizPractice) => ReactNode;
}

/** Before sending: previous attempts, then the form, or the date of the new attempt (F9). */
export function QuizEntry(props: QuizEntryProps) {
  const { attempts, questions, retryOn, error, pending, round, onSubmit, renderGhost } = props;
  return (
    <>
      <AttemptHistory attempts={attempts} />
      {error ? <InlineError message={error} /> : null}
      {retryOn !== null ? (
        <>
          <p role="status" className="rounded-xl border bg-card p-4 text-sm">
            {t("quiz.page.retryTooSoon", { date: longDay(retryOn) })}
          </p>
          {renderGhost?.()}
        </>
      ) : (
        <QuizForm
          key={round}
          questions={questions}
          disabled={pending}
          onSubmit={onSubmit}
          renderGhost={renderGhost}
        />
      )}
    </>
  );
}
