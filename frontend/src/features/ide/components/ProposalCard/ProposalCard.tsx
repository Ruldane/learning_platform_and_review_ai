import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { locationText } from "../noteText";
import type { NoteView } from "../viewTypes";
import { CodeBlock } from "./CodeBlock";
import { ProposalActions } from "./ProposalActions";

interface ProposalCardProps {
  note: NoteView;
  /** A decision is in progress: the buttons wait for the response. */
  busy: boolean;
  onAccept: () => void;
  onReject: () => void;
}

/**
 * A proposed fix: the before and after code, side by side. « Accepter » asks the
 * server to apply it (the front never rewrites the file itself); a proposal
 * that is stale, since the code has changed, is greyed out and can no longer be accepted.
 */
export function ProposalCard({ note, busy, onAccept, onReject }: ProposalCardProps) {
  const headingId = useId();
  const place = locationText(note);
  const open = note.status === "open";
  const stale = note.status === "stale";
  return (
    <article
      id={`note-${note.id}`}
      aria-labelledby={headingId}
      className={cn(
        "flex flex-col gap-2 rounded-xl border border-border bg-card p-3",
        stale && "opacity-60",
      )}
    >
      <h4 id={headingId} className="text-sm font-medium">
        {t("ide.proposal.heading", { author: note.authorLabel })}
      </h4>
      {place ? <p className="text-xs text-muted-foreground">{place}</p> : null}
      <p className="text-sm whitespace-pre-wrap">{note.content}</p>
      {open || stale ? (
        <div className="grid gap-2 sm:grid-cols-2">
          <CodeBlock
            label={t("ide.proposal.before")}
            text={note.before ?? t("ide.proposal.notFound")}
          />
          <CodeBlock label={t("ide.proposal.after")} text={note.replacement ?? ""} />
        </div>
      ) : null}
      <p className="text-xs">
        {stale ? t("ide.teacher.stale") : t(`ide.teacher.status.${note.status}`)}
      </p>
      {open || stale ? (
        <ProposalActions stale={stale} busy={busy} onAccept={onAccept} onReject={onReject} />
      ) : null}
    </article>
  );
}
