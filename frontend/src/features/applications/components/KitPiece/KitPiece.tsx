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
  /** Le kit est en cours : une pièce pas encore arrivée est « en préparation ». */
  running: boolean;
  /** Envoie le texte au serveur, qui le relit ; ne lève jamais. */
  onSave: (content: string) => Promise<KitSaveResult>;
  /** Copie un texte : l'application n'envoie rien. Une promesse rejetée signale l'échec. */
  onCopy: (text: string) => void | Promise<void>;
}

/**
 * Une pièce du kit : son nom et son statut (prête, à vérifier avec ses raisons, en échec, pas
 * encore là), son texte modifiable (enregistré seulement par le bouton), un bouton Copier par
 * texte et, pour le dossier, ses sources. Rien n'est envoyé par l'application.
 */
export function KitPiece({ piece, running, onSave, onCopy }: KitPieceProps) {
  const headingId = useId();
  const draft = useKitDraft(piece.kind, piece.content);
  const root = useRef<HTMLElement>(null);
  const actions = useKitPieceActions(root, {
    text: draft.text,
    onSaved: draft.clear,
    onSave,
    onCopy,
  });
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
            actions.clearNote();
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
        saving={actions.saving}
        note={actions.note}
        error={actions.error}
        onSave={() => void actions.save()}
      />
    </section>
  );
}
