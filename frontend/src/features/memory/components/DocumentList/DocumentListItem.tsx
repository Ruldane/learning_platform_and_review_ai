import { t } from "@/shared/i18n/t";
import { memory } from "@/shared/i18n/messages/memory";
import { Button } from "@/shared/ui/button";
import { formatDay } from "../formatDate";
import type { DocumentRow } from "../viewTypes";

interface DocumentListItemProps {
  document: DocumentRow;
  learning: boolean;
  onMarkLearned: (id: string) => void;
}

type KnownSource = keyof typeof memory.documents.sourceKind;

/** Nom lisible du type de source ; une valeur inconnue du front est affichée telle quelle. */
function sourceLabel(kind: string): string {
  return kind in memory.documents.sourceKind
    ? t(`memory.documents.sourceKind.${kind as KnownSource}`)
    : kind;
}

/** Une ligne de la liste : nom, type de source, date, statut, erreur et action « déjà appris ». */
export function DocumentListItem({ document, learning, onMarkLearned }: DocumentListItemProps) {
  // Le back pose `learned` dès le lancement : un échec ou une page rechargée ne laissent que ce
  // drapeau. Tant que rien ne tourne, un document appris reste donc relançable (sans danger : les
  // acquis déjà écrits sont reconnus).
  const canMark = document.status === "indexed";
  const relaunch = document.learned && !learning;
  return (
    <li className="flex flex-col gap-1 rounded-lg border border-border bg-card px-3 py-2">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <div className="flex flex-col">
          <span className="font-medium break-words">{document.name}</span>
          <span className="flex gap-1 text-sm text-muted-foreground">
            <span>{sourceLabel(document.source_kind)}</span>
            <span aria-hidden="true">·</span>
            <span>{formatDay(document.created_at)}</span>
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={
              document.status === "error"
                ? "text-sm font-medium text-destructive"
                : "text-sm font-medium"
            }
          >
            {t(`memory.documents.status.${document.status}`)}
          </span>
          {document.learned ? (
            <span className="text-sm text-muted-foreground">{t("memory.documents.learned")}</span>
          ) : null}
          {canMark ? (
            <Button
              variant="outline"
              size="sm"
              disabled={learning}
              onClick={() => onMarkLearned(document.id)}
            >
              {t(relaunch ? "memory.documents.relaunch" : "memory.documents.markLearned")}
            </Button>
          ) : null}
        </div>
      </div>
      {document.status === "error" && document.error ? (
        <p role="alert" className="text-sm text-destructive">
          {document.error.message}
        </p>
      ) : null}
    </li>
  );
}
