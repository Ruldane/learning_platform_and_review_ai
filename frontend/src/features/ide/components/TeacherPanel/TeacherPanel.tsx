import { useId, type Ref } from "react";
import { t } from "@/shared/i18n/t";
import { NoteCard } from "../NoteCard";
import { ProposalCard } from "../ProposalCard";
import type { NoteKind, NoteView } from "../viewTypes";

interface TeacherPanelProps {
  notes: NoteView[];
  /** Une décision sur une proposition est en cours. */
  busy: boolean;
  onAccept: (noteId: string) => void;
  onReject: (noteId: string) => void;
  /** Reçoit le focus quand une proposition quitte la liste d'attente (accepter, refuser). */
  headingRef?: Ref<HTMLHeadingElement>;
}

const GROUPS: readonly NoteKind[] = ["hint", "explanation", "annotation", "proposal", "reference"];

/**
 * Tout ce que le professeur (ou Claude) a écrit pendant la séance, par sorte : indices (avec leur
 * rang), explications, annotations de la marge, propositions à décider, renvois. Une liste
 * accessible : les annotations sont ici aussi, pas seulement dans la marge.
 */
export function TeacherPanel({ notes, busy, onAccept, onReject, headingRef }: TeacherPanelProps) {
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-3">
      <h2 id={headingId} ref={headingRef} tabIndex={-1} className="font-medium outline-none">
        {t("ide.teacher.title")}
      </h2>
      {notes.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("ide.teacher.empty")}</p>
      ) : null}
      {GROUPS.map((kind) => {
        const items = notes.filter((note) => note.kind === kind);
        if (items.length === 0) return null;
        const title = t(`ide.teacher.groups.${kind}`);
        return (
          <section key={kind} aria-label={title} className="flex flex-col gap-2">
            <h3 className="text-sm font-medium">{title}</h3>
            <ul className="flex flex-col gap-2">
              {items.map((note) => (
                <li key={note.id}>
                  {note.kind === "proposal" ? (
                    <ProposalCard
                      note={note}
                      busy={busy}
                      onAccept={() => onAccept(note.id)}
                      onReject={() => onReject(note.id)}
                    />
                  ) : (
                    <NoteCard note={note} />
                  )}
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </section>
  );
}
