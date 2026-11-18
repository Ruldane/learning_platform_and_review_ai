import { t } from "@/shared/i18n/t";
import type { NoteView } from "./viewTypes";

/** Une ligne du fil : une note rangée, ou la question qui part (affichée avant d'être relue). */
export type ChatItem =
  | { type: "note"; id: string; note: NoteView; mine: boolean; tag: string | null }
  | { type: "pending"; id: string; text: string };

/**
 * L'étiquette d'une note que January n'a pas demandée à l'instant : l'indice et son niveau, le
 * commentaire de marge, le renvoi, et « après une exécution » pour une explication du professeur
 * qui ne répond à aucune question (réussite des tests). Une réponse à une question n'en porte pas.
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

/** Le fil dans l'ordre des notes ; ses messages (`mine`) d'un côté, ceux des autres de l'autre. */
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
