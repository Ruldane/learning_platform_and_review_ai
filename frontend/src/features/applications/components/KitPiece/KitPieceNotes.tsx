import { t } from "@/shared/i18n/t";
import type { KitPieceView } from "../viewTypes";
import type { Part } from "./parts";

const count = (key: "salary" | "toComplete", n: number) =>
  t(`applications.kitPiece.${key}.${n === 1 ? "one" : "many"}`, { count: n });

/** Why a piece is « à vérifier »: each reason given by the server or the text. */
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
  // A file can be « à vérifier » with no terms: the code removed the sections without a source.
  if (list.length === 0 && piece.kind === "company_brief") {
    list.push(t("applications.kitPiece.removed"));
  }
  if (list.length > 0) return list;
  // Empty text saved: the server marks the piece « à vérifier » with no other reason.
  return [
    t(
      piece.content.trim() === "" ? "applications.kitPiece.empty" : "applications.kitPiece.generic",
    ),
  ];
}

interface KitPieceNotesProps {
  piece: KitPieceView;
  parts: Part[];
  running: boolean;
}

/** What January needs to know about the piece's state: to check (why), failed, not yet there. */
export function KitPieceNotes({ piece, parts, running }: KitPieceNotesProps) {
  if (piece.status === "to_check") {
    return (
      <div
        role="note"
        className="flex flex-col gap-1 rounded-lg border-2 border-foreground/40 bg-muted/60 p-3 text-sm"
      >
        {reasons(piece, parts).map((reason, index) => (
          <p key={index}>{reason}</p>
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
