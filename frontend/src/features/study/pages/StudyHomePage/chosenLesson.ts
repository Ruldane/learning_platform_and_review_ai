import { useLocation, useSearchParams } from "react-router";
import { clampQuestion } from "../../toView";

export interface ChosenLesson {
  lessonId: string;
  /** The lesson's passage that January asks the tutor about (already cut at 2,000 characters). */
  question: string | null;
}

/** What the navigation state carries (« Demander au tuteur »): any other content is ignored. */
function readState(state: unknown): { lessonId: string | null; question: string | null } {
  const record =
    typeof state === "object" && state !== null ? (state as Record<string, unknown>) : {};
  const lessonId =
    typeof record.lessonId === "string" && record.lessonId !== "" ? record.lessonId : null;
  const text = typeof record.question === "string" ? clampQuestion(record.question) : "";
  return { lessonId, question: text === "" ? null : text };
}

/**
 * The lesson chosen outside the day's block: the navigation state `{ lessonId, question }` (the
 * « Demander au tuteur » button) or `?lesson={id}` (no question). `null`: the day's block.
 */
export function useChosenLesson(): ChosenLesson | null {
  const location = useLocation();
  const [params] = useSearchParams();
  const fromState = readState(location.state);
  const lessonId = fromState.lessonId ?? params.get("lesson") ?? params.get("lecon");
  if (lessonId === null || lessonId === "") return null;
  return { lessonId, question: fromState.lessonId === null ? null : fromState.question };
}
