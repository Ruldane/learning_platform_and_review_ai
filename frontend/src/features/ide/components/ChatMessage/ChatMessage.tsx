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
  onOpenFile?: (path: string) => void;
}

/**
 * Un message du fil : le sien à droite, celui du professeur ou de Claude à gauche, avec l'auteur,
 * le renvoi au fichier et aux lignes. Une proposition garde sa carte (Accepter, Refuser).
 */
export function ChatMessage({
  note,
  mine,
  tag,
  busy,
  onAccept,
  onReject,
  onOpenFile,
}: ChatMessageProps) {
  const path = note.filePath;
  const where = locationText(note);
  const link =
    path && onOpenFile ? (
      <button
        type="button"
        aria-label={t("ide.teacher.openFile", { file: path })}
        onClick={() => onOpenFile(path)}
        className="rounded text-left text-xs underline underline-offset-2 focus-visible:ring-2 focus-visible:ring-ring"
      >
        {where ?? path}
      </button>
    ) : null;
  if (note.kind === "proposal") {
    return (
      <li className="flex justify-start">
        <div className="w-full max-w-[95%]">
          <ProposalCard note={note} busy={busy} onAccept={onAccept} onReject={onReject} />
          {link}
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
      context={link ? null : where}
      muted={stale}
    >
      {link}
      {stale ? <p className="text-xs font-medium">{t("ide.teacher.stale")}</p> : null}
    </Message>
  );
}
