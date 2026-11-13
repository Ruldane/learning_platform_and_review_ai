import { Fragment } from "react";
import { t } from "@/shared/i18n/t";
import type { DiffSegment } from "./wordDiff";

interface DiffSideProps {
  segments: DiffSegment[];
  side: "before" | "after";
  /** Dit pourquoi ce côté est vide (ligne ajoutée, ligne retirée). */
  empty: string;
}

/**
 * Un côté du diff. Le retrait est barré (`<del>`), l'ajout souligné (`<ins>`), et un mot caché
 * pour les lecteurs d'écran les nomme : la couleur n'est jamais le seul signal.
 */
export function DiffSide({ segments, side, empty }: DiffSideProps) {
  const kept = segments.filter(
    (segment) => segment.kind === "same" || segment.kind === (side === "before" ? "del" : "add"),
  );
  if (kept.length === 0) return <p className="text-sm italic text-muted-foreground">{empty}</p>;
  return (
    <p className="text-sm break-words">
      {kept.map((segment, index) => (
        <Fragment key={index}>
          {index > 0 ? " " : null}
          {segment.kind === "same" ? (
            segment.text
          ) : segment.kind === "add" ? (
            <ins className="font-medium underline decoration-2 underline-offset-2">
              {segment.text}
              <span className="sr-only"> ({t("cv.mod.added")})</span>
            </ins>
          ) : (
            <del className="text-muted-foreground line-through decoration-2">
              {segment.text}
              <span className="sr-only"> ({t("cv.mod.removed")})</span>
            </del>
          )}
        </Fragment>
      ))}
    </p>
  );
}
