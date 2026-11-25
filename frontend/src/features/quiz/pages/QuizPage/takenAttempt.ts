import type { ResponseTiming } from "@/shared/lib/concentration";
import type { AnswerDraft, QuestionView } from "../../components/viewTypes";

/** A sent attempt: the questions as they were displayed, and the answers (to resend them). */
export interface TakenAttempt {
  attemptId: string;
  questions: QuestionView[];
  /** `null` when the attempt is a grading resumed after a page reload. */
  drafts: AnswerDraft[] | null;
  elapsedMs?: number;
  timings?: ResponseTiming[];
}
