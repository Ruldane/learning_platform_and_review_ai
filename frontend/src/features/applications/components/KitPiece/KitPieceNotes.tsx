import { t } from "@/shared/i18n/t";
import type { KitPieceView } from "../viewTypes";
import type { Part } from "./parts";

const count = (key: "salary" | "toComplete", n: number) =>
  t(`applications.kitPiece.${key}.${n === 1 ? "one" : "many"}`, { count: n });

/** Pourquoi une pièce est « à vérifier » : chaque raison que le serveur ou le texte donne. */
function reasons(piece: KitPieceView, parts: Part[]): string[] {
  const list: string[] = [];
  if (piece.flags.length > 0) {
    list.push(
      t("applications.kitPiece.flags", { terms: piece.flags.join(", ") }),
      t("applications.kitPiece.flagsAdvice"),
    );
  }
  if (piece.salaryFields > 0) list.push(count("salary", piece.salaryFields));
  const toComplete = parts.filter((part) => part.blank === "complete").length;
  if (toComplete > 0) list.push(count("toComplete", toComplete));
  // Un dossier peut être « à vérifier » sans aucun terme : le code a retiré les sections sans source.
  if (list.length === 0 && piece.kind === "company_brief") {
    list.push(t("applications.kitPiece.removed"));
  }
  return list.length > 0 ? list : [t("applications.kitPiece.generic")];
}

interface KitPieceNotesProps {
  piece: KitPieceView;
  parts: Part[];
  running: boolean;
}

/** Ce que January doit savoir de l'état de la pièce : à vérifier (pourquoi), en échec, pas encore là. */
export function KitPieceNotes({ piece, parts, running }: KitPieceNotesProps) {
  if (piece.status === "to_check") {
    return (
      <div
        role="note"
        className="flex flex-col gap-1 rounded-lg border-2 border-foreground/40 bg-muted/60 p-3 text-sm"
      >
        {reasons(piece, parts).map((reason) => (
          <p key={reason}>{reason}</p>
        ))}
      </div>
    );
  }
  if (piece.status === "failed") {
    return (
      <div
        role="note"
        className="flex flex-col gap-1 rounded-lg border-2 border-destructive/50 bg-muted/60 p-3 text-sm"
      >
        <p>
          {piece.error
            ? t("applications.kitPiece.failedReason", { error: piece.error })
            : t("applications.kitPiece.failedNoReason")}
        </p>
        <p>{t("applications.kitPiece.failedAdvice")}</p>
      </div>
    );
  }
  if (piece.status === "pending") {
    return (
      <p className="text-sm text-muted-foreground">
        {running ? t("applications.kitPiece.pendingText") : t("applications.kitPiece.pendingIdle")}
      </p>
    );
  }
  return null;
}
