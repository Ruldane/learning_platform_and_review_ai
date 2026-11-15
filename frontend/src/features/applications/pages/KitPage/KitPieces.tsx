import { t } from "@/shared/i18n/t";
import { KitPiece } from "../../components/KitPiece";
import { copyToClipboard } from "../../hooks/useReminderHandlers";
import type { KitKindView, KitPieceView, KitSaveResult } from "../../types";

interface KitPiecesProps {
  pieces: KitPieceView[];
  running: boolean;
  onSave: (kind: KitKindView, content: string) => Promise<KitSaveResult>;
}

/** Les sept pièces dans l'ordre du serveur ; avant tout lancement, une seule phrase au lieu de sept cases vides. */
export function KitPieces({ pieces, running, onSave }: KitPiecesProps) {
  const arrived = pieces.filter((piece) => piece.status !== "pending").length;
  if (arrived === 0 && !running) {
    return <p className="text-muted-foreground">{t("applications.kitPage.emptyHint")}</p>;
  }
  return (
    <div className="flex flex-col gap-3">
      {running ? (
        <p className="text-sm text-muted-foreground">
          {t(`applications.kitPage.progress.${arrived === 1 ? "one" : "many"}`, { count: arrived })}
        </p>
      ) : null}
      <ul aria-label={t("applications.kitPage.piecesLabel")} className="flex flex-col gap-3">
        {pieces.map((piece) => (
          <li key={piece.kind}>
            <KitPiece
              piece={piece}
              running={running}
              onSave={(content) => onSave(piece.kind, content)}
              onCopy={copyToClipboard}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}
