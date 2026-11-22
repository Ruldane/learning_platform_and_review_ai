import { t } from "@/shared/i18n/t";
import { ChatMessage as Message } from "@/shared/ui/ChatMessage";
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
  if (note.kind === "proposal") {
    return (
      <li className="flex justify-start">
        <div className="w-full max-w-[95%]">
          <ProposalCard note={note} busy={busy} onAccept={onAccept} onReject={onReject} />
        </div>
      </li>
    );
  }
  const stale = note.status === "stale";
  return (
    <Message
      id={`note-${note.id}`}
      author={mine ? "user" : note.author}
      label={note.authorLabel}
      content={note.content}
      tag={tag}
      context={locationText(note)}
      muted={stale}
    >
      {stale ? <p className="text-xs font-medium">{t("ide.teacher.stale")}</p> : null}
    </Message>
  );
}
