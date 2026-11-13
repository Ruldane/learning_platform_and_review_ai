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

/** `AAAA-MM-JJ` d'un jour que le back peut rendre avec une heure ; `null` si ce n'est pas un jour. */
export function dayOf(value: string | null | undefined): string | null {
  const day = typeof value === "string" ? value.slice(0, 10) : "";
  return /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : null;
}

/** Seuil de réussite d'un quiz (le back décide ; sert seulement à retrouver la date d'un nouvel essai). */
const PASS_PERCENT = 80;
/** Délai du nouvel essai après un échec (F9) : J+2. */
const RETRY_DAYS = 2;

/** Le jour, s'il est encore à venir (après `today`) ; sinon `null` : une date passée ne se dit plus. */
export function upcoming(day: string | null, today: string = localDay()): string | null {
  return day !== null && day > today ? day : null;
}

/**
 * Le nouvel essai d'un quiz, déduit de ses tentatives (le contrat de `QuizOut` ne le donne pas) :
 * la dernière tentative notée sous 80 % ouvre un nouvel essai deux jours après son jour local.
 * `null` quand rien n'attend ou que la date est passée ; le 409 `retry_too_soon` reste la garde.
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

/** Un score en pourcentage entier de 0 à 100 (le back en rend déjà un ; on borne par prudence). */
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

/** Une ligne de la liste ; la date du nouvel essai n'est gardée que si elle est à venir. */
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
 * Le résultat d'une tentative : chaque `ResultOut` est joint à l'énoncé de sa question (le back ne
 * rend que `question_id`), tel qu'il s'affichait à l'envoi (l'ordre change à chaque essai, F27).
 * La date du nouvel essai n'est gardée que si elle est à venir.
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
