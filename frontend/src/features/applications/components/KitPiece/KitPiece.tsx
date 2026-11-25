import { useId, useRef } from "react";
import { t } from "@/shared/i18n/t";
import type { KitPieceView, KitSaveResult } from "../viewTypes";
import { KitPartList } from "./KitPartList";
import { KitPieceFooter } from "./KitPieceFooter";
import { KitPieceHeader } from "./KitPieceHeader";
import { KitPieceNotes } from "./KitPieceNotes";
import { KitSources } from "./KitSources";
import { useKitDraft } from "./useKitDraft";
import { useKitPieceActions } from "./useKitPieceActions";

interface KitPieceProps {
  piece: KitPieceView;
  /** The kit is running: a piece not yet arrived is « en préparation ». */
  running: boolean;
  /** Sends the text to the server, which re-reads it; never throws. */
  onSave: (content: string) => Promise<KitSaveResult>;
  /** Copies a text: the app sends nothing. A rejected promise signals the failure. */
  onCopy: (text: string) => void | Promise<void>;
}

/**
 * A kit piece: its name and status (ready, to check with its reasons, failed, not
 * yet there), its editable text (saved only by the button), a Copy button per
 * text and, for the file, its sources. The app sends nothing.
 */
export function KitPiece({ piece, running, onSave, onCopy }: KitPieceProps) {
  const headingId = useId();
  const draft = useKitDraft(piece.kind, piece.content);
  const root = useRef<HTMLElement>(null);
  const actions = useKitPieceActions(root, draft, { onSave, onCopy });
  const title = t(`applications.kitPiece.title.${piece.kind}`);
  const editable = piece.status !== "pending";

  return (
    <section
      ref={root}
      aria-labelledby={headingId}
      className="flex flex-col gap-3 rounded-xl border bg-card p-4 text-sm"
    >
      <KitPieceHeader piece={piece} headingId={headingId} running={running} />
      <KitPieceNotes piece={piece} parts={draft.parts} running={running} />
      {editable ? (
        <KitPartList
          parts={draft.parts}
          pieceTitle={title}
          busy={actions.saving}
          onChange={(key, text) => {
            actions.edited(key);
            draft.change(key, text);
          }}
          onCopy={(text) => void actions.copy(text)}
        />
      ) : null}
      {draft.changedUnder ? (
        <p role="status" className="text-xs text-muted-foreground">
          {t("applications.kitPiece.changedUnder")}
        </p>
      ) : null}
      <KitSources sources={piece.sources} />
      <KitPieceFooter
        title={title}
        editable={editable}
        dirty={draft.dirty}
        tooLong={draft.tooLong}
        saving={actions.saving}
        note={actions.note}
        error={actions.error}
        onSave={() => void actions.save()}
      />
    </section>
  );
}
