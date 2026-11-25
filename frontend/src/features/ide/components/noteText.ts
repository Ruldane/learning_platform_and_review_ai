import { t } from "@/shared/i18n/t";
import type { NoteView } from "./viewTypes";

/** « main.py, ligne 4 » or « main.py, lignes 4 à 6 »; `null` for a note with no location. */
export function locationText(note: NoteView): string | null {
  if (!note.filePath || note.lineStart === null) return null;
  const end = note.lineEnd;
  const lines =
    end !== null && end > note.lineStart
      ? t("ide.teacher.linesRange", { start: note.lineStart, end })
      : t("ide.teacher.lines", { start: note.lineStart });
  return t("ide.teacher.inFile", { file: note.filePath, lines });
}
