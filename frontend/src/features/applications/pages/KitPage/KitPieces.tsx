import { t } from "@/shared/i18n/t";
import { copyToClipboard } from "../../clipboard";
import { KitPiece } from "../../components/KitPiece";
import type { KitKindView, KitPieceView, KitSaveResult } from "../../types";
import { useArrivedCount } from "./useArrivedCount";

interface KitPiecesProps {
  pieces: KitPieceView[];
  running: boolean;
  onSave: (kind: KitKindView, content: string) => Promise<KitSaveResult>;
}

/** Show the pieces in server order, with a single empty state before the first run. */
export function KitPieces({ pieces, running, onSave }: KitPiecesProps) {
  const arrived = useArrivedCount(pieces, running);
  if (!running && pieces.every((piece) => piece.status === "pending")) {
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
