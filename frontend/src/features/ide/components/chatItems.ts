import { t } from "@/shared/i18n/t";
import type { NoteView } from "./viewTypes";

/** A thread row: a filed note, or the question being sent (shown before it is re-read). */
export type ChatItem =
  | { type: "note"; id: string; note: NoteView; mine: boolean; tag: string | null }
  | { type: "pending"; id: string; text: string };

/**
 * The label of a note January did not just ask for: the hint and its level, the
 * margin comment, the link, and « après une exécution » for a teacher explanation
 * that answers no question (tests passing). An answer to a question carries none.
 */
export function tagOf(note: NoteView, previous: NoteView | undefined): string | null {
  if (note.kind === "hint") {
    return note.hintLevel === null ? null : t("ide.teacher.hintLevel", { level: note.hintLevel });
  }
  if (note.kind === "annotation") return t("ide.chat.tags.margin");
  if (note.kind === "reference") return t("ide.chat.tags.reference");
  if (note.kind === "explanation" && note.author === "professor" && previous?.kind !== "question") {
    return t("ide.chat.tags.afterRun");
  }
  return null;
}

/** The thread in note order; its messages (`mine`) on one side, the others' on the other. */
export function toChatItems(notes: NoteView[], pendingQuestion: string | null): ChatItem[] {
  const items: ChatItem[] = notes.map((note, index) => ({
    type: "note",
    id: note.id,
    note,
    mine: note.author === "user",
    tag: tagOf(note, notes[index - 1]),
  }));
  if (pendingQuestion) items.push({ type: "pending", id: "pending", text: pendingQuestion });
  return items;
}
