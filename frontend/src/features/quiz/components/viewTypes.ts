/** View types for the quiz and review components: independent of the API contract (D34). */

export type QuestionTypeView = "mcq" | "short" | "code" | "explain";

export interface QuestionView {
  id: string;
  rank: number;
  type: QuestionTypeView;
  prompt: string;
  /** Code to read, shown as is (never interpreted); `null` when the question has none. */
  code: string | null;
  /** The choices of an MCQ; empty for the other types. */
  choices: string[];
}

/** An answer to a question: `choice` for an MCQ, `text` for the other types. */
export interface AnswerDraft {
  question_id: string;
  choice: number | null;
  text: string;
}

/** A question's result, joined to its prompt by the page. */
export interface QuestionResultView {
  questionId: string;
  rank: number;
  prompt: string;
  /** 0, 0.5 or 1: the grid allows nothing else. */
  points: number;
  correctAnswer: string;
  explanation: string;
  /** Feedback on January's answer; empty for an MCQ. */
  feedback: string;
}

/** What follows a failure: reviews added, a new attempt, tasks with no room in the budget. */
export interface FollowupView {
  revisionTasks: string[];
  /** Day `YYYY-MM-DD` of the new attempt, if still to come; `null` otherwise. */
  retryOn: string | null;
  /** Reviews that no week of the budget could take. */
  unplaced: number;
}

export interface AttemptResultView {
  /** Whole percentage, 0 to 100. */
  score: number;
  /** True at 80%: the skill moves to `valide`. The decision stays with the back end. */
  passed: boolean;
  results: QuestionResultView[];
  /** `null` when the quiz is passed. */
  followup: FollowupView | null;
}

export interface CardView {
  id: string;
  front: string;
  back: string;
  skill: string | null;
}

export type QuizStatusView = "generating" | "ready" | "failed";

/** A list row: a module, its quiz if it exists, the best score. */
export interface QuizSummaryView {
  moduleId: string;
  moduleTitle: string;
  weekRank: number;
  quizId: string | null;
  status: QuizStatusView | null;
  /** Best score as a percentage; `null` until an attempt is graded. */
  bestScore: number | null;
  /** Day `YYYY-MM-DD` of the next attempt after a failure, if still to come (else `null`). */
  retryOn: string | null;
}
