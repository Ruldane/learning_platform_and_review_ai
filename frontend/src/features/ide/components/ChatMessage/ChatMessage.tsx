import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { ChatMarkdown } from "../ChatMarkdown";
import { locationText } from "../noteText";
import { ProposalCard } from "../ProposalCard";
import type { NoteView } from "../viewTypes";

interface ChatMessageProps {
  note: NoteView;
  /** Son message : aligné à droite, texte brut (ce qu'elle a tapé). */
  mine: boolean;
  /** « indice 2 », « après une exécution »… : pourquoi cette note est arrivée sans question. */
  tag: string | null;
  /** Une décision sur une proposition est en cours. */
  busy: boolean;
  onAccept: () => void;
  onReject: () => void;
}

/**
 * Un message du fil : le sien à droite, celui du professeur ou de Claude à gauche, avec l'auteur,
 * le renvoi au fichier et aux lignes. Une proposition garde sa carte (Accepter, Refuser).
 */
export function ChatMessage({ note, mine, tag, busy, onAccept, onReject }: ChatMessageProps) {
  const labelId = useId();
  if (note.kind === "proposal") {
    return (
      <li className="flex justify-start">
        <div className="w-full max-w-[95%]">
          <ProposalCard note={note} busy={busy} onAccept={onAccept} onReject={onReject} />
        </div>
      </li>
    );
  }
  const place = locationText(note);
  const stale = note.status === "stale";
  return (
    <li className={cn("flex", mine ? "justify-end" : "justify-start")}>
      <article
        id={`note-${note.id}`}
        aria-labelledby={labelId}
        data-author={mine ? "user" : note.author}
        className={cn(
          "flex max-w-[90%] flex-col gap-1 rounded-2xl border px-3 py-2",
          mine ? "border-transparent bg-accent text-accent-foreground" : "border-border bg-card",
          stale && "opacity-60",
        )}
      >
        <p id={labelId} className="text-xs font-medium">
          {note.authorLabel}
          {tag ? (
            <>
              {" "}
              <span className="font-normal text-muted-foreground">· {tag}</span>
            </>
          ) : null}
        </p>
        {place ? <p className="text-xs text-muted-foreground">{place}</p> : null}
        {mine ? (
          <p className="text-sm whitespace-pre-wrap">{note.content}</p>
        ) : (
          <ChatMarkdown>{note.content}</ChatMarkdown>
        )}
        {stale ? <p className="text-xs font-medium">{t("ide.teacher.stale")}</p> : null}
      </article>
    </li>
  );
}
