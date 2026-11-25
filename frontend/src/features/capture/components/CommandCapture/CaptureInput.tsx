import { t } from "@/shared/i18n/t";
import type { CaptureSource } from "../viewTypes";
import { FilePicker } from "./FilePicker";
import { LinkNoteForm } from "./LinkNoteForm";

interface CaptureInputProps {
  /** The field draft (kept when the dialog closes). */
  draft: string;
  onDraft: (draft: string) => void;
  /** A send is in progress (link, note or file): everything is disabled. */
  busy: boolean;
  /** The file is being imported (before the capture starts). */
  uploading: boolean;
  /** Message from a server refusal, below the field. */
  error: string | null;
  onSubmit: (source: CaptureSource) => void;
  onFile: (file: File) => void;
}

/**
 * The dialog content before the start: the single field (link or note, Ctrl+Enter sends), then
 * dropping or choosing a file.
 */
export function CaptureInput(props: CaptureInputProps) {
  const { draft, onDraft, busy, uploading, error, onSubmit, onFile } = props;
  return (
    <div className="flex flex-col gap-4">
      <LinkNoteForm
        value={draft}
        onValueChange={onDraft}
        busy={busy}
        uploading={uploading}
        error={error}
        onSubmit={onSubmit}
      />
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
