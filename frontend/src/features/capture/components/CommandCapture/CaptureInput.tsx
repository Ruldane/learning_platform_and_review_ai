import { t } from "@/shared/i18n/t";
import type { CaptureSource } from "../viewTypes";
import { FilePicker } from "./FilePicker";
import { LinkNoteForm } from "./LinkNoteForm";

interface CaptureInputProps {
  /** Un envoi est en cours (lien, note ou fichier) : tout est désactivé. */
  busy: boolean;
  /** Le fichier est en cours d'import (avant le départ de la capture). */
  uploading: boolean;
  /** Message d'un refus du serveur, sous le champ. */
  error: string | null;
  onSubmit: (source: CaptureSource) => void;
  onFile: (file: File) => void;
}

/**
 * Le contenu du dialogue avant le départ : le champ unique (lien ou note, Ctrl+Entrée envoie) puis
 * le dépôt ou le choix d'un fichier.
 */
export function CaptureInput({ busy, uploading, error, onSubmit, onFile }: CaptureInputProps) {
  return (
    <div className="flex flex-col gap-4">
      <LinkNoteForm busy={busy} uploading={uploading} error={error} onSubmit={onSubmit} />
      <p className="text-center text-xs text-muted-foreground">{t("capture.input.or")}</p>
      <FilePicker disabled={busy} onFile={onFile} />
      {uploading ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("capture.input.uploading")}
        </p>
      ) : null}
    </div>
  );
}
