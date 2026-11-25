import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ExportFormat } from "./exportBoard";

interface BoardToolbarProps {
  /** The canvas is ready: export is possible. */
  canExport: boolean;
  /** January changed the board since the last reference. */
  canSend: boolean;
  sending: boolean;
  readOnly: boolean;
  error: string | null;
  saveLabel?: string | undefined;
  onExport: (format: ExportFormat) => void;
  onSend: () => void;
}

const EXPORTS: { format: ExportFormat; label: "exportPng" | "exportSvg" | "exportScene" }[] = [
  { format: "png", label: "exportPng" },
  { format: "svg", label: "exportSvg" },
  { format: "scene", label: "exportScene" },
];

/** Exports (PNG, SVG, .excalidraw) and sending January's changes to the agents. */
export function BoardToolbar(props: BoardToolbarProps) {
  const { canExport, canSend, sending, readOnly, error, onExport, onSend } = props;
  return (
    <div className="flex flex-col gap-2">
      <div role="toolbar" aria-label={t("session.board.toolbar")} className="flex flex-wrap gap-2">
        {EXPORTS.map(({ format, label }) => (
          <Button
            key={format}
            variant="outline"
            size="sm"
            disabled={!canExport}
            onClick={() => onExport(format)}
          >
            {t(`session.board.${label}`)}
          </Button>
        ))}
        {readOnly ? null : (
          <Button size="sm" disabled={!canSend || sending} onClick={onSend}>
            {sending ? t("session.board.sending") : props.saveLabel ?? t("session.board.send")}
          </Button>
        )}
      </div>
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
