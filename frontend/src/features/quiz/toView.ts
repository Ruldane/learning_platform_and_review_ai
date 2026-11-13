import type {
  AttemptResultView,
  CardView,
  QuestionResultView,
  QuestionView,
  QuizSummaryView,
} from "./components/viewTypes";
import type { AttemptOut, FlashcardOut, QuestionOut, QuizSummaryOut } from "./types";

/** `AAAA-MM-JJ` d'un jour que le back peut rendre avec une heure ; `null` si ce n'est pas un jour. */
export function dayOf(value: string | null | undefined): string | null {
  const day = typeof value === "string" ? value.slice(0, 10) : "";
  return /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : null;
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

export function toQuizSummaryView(item: QuizSummaryOut): QuizSummaryView {
  return {
    moduleId: item.module_id,
    moduleTitle: item.module_title,
    weekRank: item.week_rank,
    quizId: item.quiz_id,
    status: item.status,
    bestScore: item.best_score === null ? null : percent(item.best_score),
    retryOn: dayOf(item.retry_on),
  };
}

/**
 * Le résultat d'une tentative : chaque `ResultOut` est joint à l'énoncé de sa question (le back ne
 * rend que `question_id`), tel qu'il s'affichait à l'envoi (l'ordre change à chaque essai, F27).
 */
export function toAttemptResultView(
  attempt: AttemptOut,
  questions: readonly QuestionView[],
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
          retryOn: dayOf(followup.retry_on),
          unplaced: followup.unplaced,
        }
      : null,
  };
}

export function toCardView({ id, front, back, skill }: FlashcardOut): CardView {
  return { id, front, back, skill };
}
