import type { BlockView, StudySummaryView, TutorOptionView } from "./components/viewTypes";
import type { BlockOut, InterruptOption, StudySessionOut } from "./types";

/** The day's block as `BlockCard` displays it. */
export function toBlockView(block: BlockOut): BlockView {
  return {
    lessonTitle: block.lesson_title,
    moduleTitle: block.module_title,
    tasks: block.tasks.map(({ id, title, type, minutes }) => ({ id, title, type, minutes })),
  };
}

/** Summary of a finished session (`StudySummaryCard`); a missing one becomes an empty text. */
export function toSummaryView(session: StudySessionOut): StudySummaryView {
  return {
    moduleTitle: session.module_title,
    lessonTitle: session.lesson_title,
    minutes: session.minutes,
    summary: session.summary ?? "",
    tasksDone: session.tasks_done,
    flashcardsCreated: session.flashcards_created,
    skills: session.skills.map(({ name, level }) => ({ name, level })),
  };
}

/** The options of a Tutor question: values and labels come from the back end (F15). */
export function toTutorOptions(options: InterruptOption[] | undefined): TutorOptionView[] {
  return (options ?? []).map(({ value, label }) => ({ value, label }));
}

/** Maximum length of `StudyStart.question` (contract). */
export const MAX_QUESTION_CHARS = 2000;

/** Cuts a passage at 2,000 characters (by code points: never in the middle of a character). */
export function clampQuestion(passage: string): string {
  const chars = Array.from(passage.trim());
  return chars.length > MAX_QUESTION_CHARS
    ? chars.slice(0, MAX_QUESTION_CHARS).join("")
    : chars.join("");
}

/** Identifier of the open session, read from the details of a 409 `study_already_open`. */
export function openSessionIn(details: unknown): string | null {
  const id = (details as { study_session_id?: unknown } | null)?.study_session_id;
  return typeof id === "string" && id !== "" ? id : null;
}
