import { t } from "@/shared/i18n/t";
import { ChatMessage as Message } from "@/shared/ui/ChatMessage";
import { locationText } from "../noteText";
import { ProposalCard } from "../ProposalCard";
import type { NoteView } from "../viewTypes";

interface ChatMessageProps {
  note: NoteView;
  /** The learner's message: aligned right, plain text (what they typed). */
  mine: boolean;
  /** « indice 2 », « après une exécution »…: why this note arrived without a question. */
  tag: string | null;
  /** A decision on a proposal is in progress. */
  busy: boolean;
  onAccept: () => void;
  onReject: () => void;
  onOpenFile?: (path: string) => void;
}

/**
 * A chat message: learner on the right, teacher or Claude on the left, with the author,
 * the link to the file and lines. A proposal keeps its card (Accepter, Refuser).
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
