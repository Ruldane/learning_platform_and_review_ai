import { t } from "@/shared/i18n/t";
import { memory } from "@/shared/i18n/messages/memory";
import type { RunSource } from "@/shared/lib/runSource";
import { useLaunchSource } from "@/shared/session-ui";
import { formatDay } from "../formatDate";
import type { DocumentRow } from "../viewTypes";
import { MarkLearnedAction } from "./MarkLearnedAction";

interface DocumentListItemProps {
  document: DocumentRow;
  learning: boolean;
  onMarkLearned: (id: string, source?: RunSource) => void;
}

type KnownSource = keyof typeof memory.documents.sourceKind;

/** Readable name of the source type; a value unknown to the front end is shown as is. */
function sourceLabel(kind: string): string {
  return kind in memory.documents.sourceKind
    ? t(`memory.documents.sourceKind.${kind as KnownSource}`)
    : kind;
}

/** A list row: name, source type, date, status, error and the « déjà appris » action. */
export function DocumentListItem({ document, learning, onMarkLearned }: DocumentListItemProps) {
  // The back end sets `learned` as soon as it starts: a failure or a reloaded page leaves only that
  // flag. While nothing runs, a learned document can be run again (harmless: the
  // acquired items already written are recognised).
  const provider = useLaunchSource();
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
            <MarkLearnedAction
              learning={learning}
              relaunch={relaunch}
              launchMenu={provider.menu}
              onClick={() =>
                provider.source === undefined
                  ? onMarkLearned(document.id)
                  : onMarkLearned(document.id, provider.source)
              }
            />
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
