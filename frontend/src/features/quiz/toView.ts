import type {
  AttemptResultView,
  CardView,
  QuestionResultView,
  QuestionView,
  QuizSummaryView,
} from "./components/viewTypes";
import { addDays, localDay } from "@/shared/lib/format";
import type {
  AttemptOut,
  AttemptSummaryOut,
  FlashcardOut,
  QuestionOut,
  QuizSummaryOut,
} from "./types";

/** `YYYY-MM-DD` of a day the back end may return with a time; `null` if it is not a day. */
export function dayOf(value: string | null | undefined): string | null {
  const day = typeof value === "string" ? value.slice(0, 10) : "";
  return /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : null;
}

/** Pass mark of a quiz (the back end decides; only used to find a new attempt's date). */
const PASS_PERCENT = 80;
/** Wait before the new attempt after a failure (F9): two days. */
const RETRY_DAYS = 2;

/** The day, if still to come (after `today`); otherwise `null`: a past date is no longer shown. */
export function upcoming(day: string | null, today: string = localDay()): string | null {
  return day !== null && day > today ? day : null;
}

/**
 * A quiz's new attempt, worked out from its attempts (the `QuizOut` contract does not give it):
 * the latest graded attempt below 80% opens a new attempt two days after its local day.
 * `null` when nothing is pending or the date has passed; the 409 `retry_too_soon` stays the guard.
 */
export function pendingRetryOn(
  attempts: readonly AttemptSummaryOut[],
  today: string = localDay(),
): string | null {
  const graded = attempts
    .filter((attempt) => attempt.status === "graded" && attempt.score !== null)
    .sort((a, b) => a.created_at.localeCompare(b.created_at));
  const last = graded.at(-1);
  if (!last || (last.score ?? 0) >= PASS_PERCENT) return null;
  return upcoming(addDays(localDay(new Date(last.created_at)), RETRY_DAYS), today);
}

/** A score as a whole percentage, 0 to 100 (already sent by the back end; clamped to be safe). */
export function percent(score: number): number {
  return Math.min(100, Math.max(0, Math.round(score)));
}

export function toQuestionViews(questions: QuestionOut[]): QuestionView[] {
  return questions.map(({ id, rank, type, prompt, code, choices }) => ({
    id,
    rank,
    type,
    prompt,
    code,
    choices,
  }));
}

/** A list row; the new attempt's date is kept only if it is still to come. */
export function toQuizSummaryView(item: QuizSummaryOut, today?: string): QuizSummaryView {
  return {
    moduleId: item.module_id,
    moduleTitle: item.module_title,
    weekRank: item.week_rank,
    quizId: item.quiz_id,
    status: item.status,
    bestScore: item.best_score === null ? null : percent(item.best_score),
    retryOn: upcoming(dayOf(item.retry_on), today),
  };
}

/**
 * An attempt's result: each `ResultOut` is joined to its question's prompt (the back end only
 * returns `question_id`), as shown at the send (the order changes each attempt, F27).
 * The new attempt's date is kept only if it is still to come.
 */
export function toAttemptResultView(
  attempt: AttemptOut,
  questions: readonly QuestionView[],
  today?: string,
): AttemptResultView {
  const results = attempt.results.map((result, index): QuestionResultView => {
    const question = questions.find((candidate) => candidate.id === result.question_id);
    return {
      questionId: result.question_id,
      rank: question?.rank ?? index + 1,
      prompt: question?.prompt ?? "",
      points: result.points,
      correctAnswer: result.correct_answer,
      explanation: result.explanation,
      feedback: result.feedback,
    };
  });
  const { followup } = attempt;
  return {
    score: percent(attempt.score ?? 0),
    passed: attempt.passed === true,
    results,
    followup: followup
      ? {
          revisionTasks: followup.revision_tasks,
          retryOn: upcoming(dayOf(followup.retry_on), today),
          unplaced: followup.unplaced,
        }
      : null,
  };
}

export function toCardView({ id, front, back, skill }: FlashcardOut): CardView {
  return { id, front, back, skill };
}
