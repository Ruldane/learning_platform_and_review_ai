import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { locationText } from "../noteText";
import type { NoteView } from "../viewTypes";

interface NoteCardProps {
  note: NoteView;
}

/**
 * Une note qui n'attend rien de toi : indice, explication, annotation ou renvoi. Périmée (le code
 * a changé depuis), elle est grisée et le dit en toutes lettres.
 */
export function NoteCard({ note }: NoteCardProps) {
  const headingId = useId();
  const place = locationText(note);
  const stale = note.status === "stale";
  return (
    <article
      id={`note-${note.id}`}
      aria-labelledby={headingId}
      className={cn(
        "flex flex-col gap-1 rounded-xl border border-border bg-card p-3",
        stale && "opacity-60",
      )}
    >
      <p id={headingId} className="text-sm font-medium">
        {note.hintLevel === null
          ? note.authorLabel
          : `${note.authorLabel} · ${t("ide.teacher.hintLevel", { level: note.hintLevel })}`}
      </p>
      {place ? <p className="text-xs text-muted-foreground">{place}</p> : null}
      <p className="text-sm whitespace-pre-wrap">{note.content}</p>
      {stale ? <p className="text-xs font-medium">{t("ide.teacher.stale")}</p> : null}
    </article>
  );
}
