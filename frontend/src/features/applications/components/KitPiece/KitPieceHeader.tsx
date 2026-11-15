import { t } from "@/shared/i18n/t";
import type { KitPieceView } from "../viewTypes";
import { KitStatusBadge } from "./KitStatusBadge";

interface KitPieceHeaderProps {
  piece: KitPieceView;
  headingId: string;
  running: boolean;
}

/** Le nom de la pièce, son statut, « modifiée par toi » et le nombre de mots. */
export function KitPieceHeader({ piece, headingId, running }: KitPieceHeaderProps) {
  const { words } = piece;
  return (
    <header className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <h2 id={headingId} className="text-base font-medium">
        {t(`applications.kitPiece.title.${piece.kind}`)}
      </h2>
      <KitStatusBadge status={piece.status} running={running} />
      {piece.edited ? (
        <span className="text-xs text-muted-foreground">{t("applications.kitPiece.edited")}</span>
      ) : null}
      {words !== null && piece.status !== "pending" ? (
        <span className="text-xs text-muted-foreground tabular-nums">
          {t(`applications.kitPiece.words.${words === 1 ? "one" : "many"}`, { count: words })}
        </span>
      ) : null}
    </header>
  );
}
