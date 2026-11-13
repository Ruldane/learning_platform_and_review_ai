import type { BlockView, StudySummaryView, TutorOptionView } from "./components/viewTypes";
import type { BlockOut, InterruptOption, StudySessionOut } from "./types";

/** Le bloc du jour tel que l'affiche `BlockCard`. */
export function toBlockView(block: BlockOut): BlockView {
  return {
    lessonTitle: block.lesson_title,
    moduleTitle: block.module_title,
    tasks: block.tasks.map(({ id, title, type, minutes }) => ({ id, title, type, minutes })),
  };
}

/** Le bilan d'une session terminée (`StudySummaryCard`) ; un résumé absent devient un texte vide. */
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

/** Les options d'une question du Tuteur : valeurs et libellés viennent du back (F15). */
export function toTutorOptions(options: InterruptOption[] | undefined): TutorOptionView[] {
  return (options ?? []).map(({ value, label }) => ({ value, label }));
}

/** Longueur maximale de `StudyStart.question` (contrat). */
export const MAX_QUESTION_CHARS = 2000;

/** Coupe un passage à 2 000 caractères (par points de code : jamais au milieu d'un caractère). */
export function clampQuestion(passage: string): string {
  const chars = Array.from(passage.trim());
  return chars.length > MAX_QUESTION_CHARS
    ? chars.slice(0, MAX_QUESTION_CHARS).join("")
    : chars.join("");
}

/** Identifiant de la session ouverte lu dans les détails d'un 409 `study_already_open`. */
export function openSessionIn(details: unknown): string | null {
  const id = (details as { study_session_id?: unknown } | null)?.study_session_id;
  return typeof id === "string" && id !== "" ? id : null;
}
