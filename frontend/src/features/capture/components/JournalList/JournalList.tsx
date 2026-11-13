import { useMemo } from "react";
import { t } from "@/shared/i18n/t";
import { longDay } from "@/shared/lib/format";
import { Button } from "@/shared/ui/button";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import type { JournalEntryView, JournalKindView } from "../viewTypes";
import { JournalEntry } from "./JournalEntry";
import { KindFilter } from "./KindFilter";
import { groupByWeek } from "./groupByWeek";

interface JournalListProps {
  entries: JournalEntryView[];
  /** Filtre courant (`null` : tous les types). */
  kind: JournalKindView | null;
  onKindChange: (kind: JournalKindView | null) => void;
  hasMore: boolean;
  loadingMore: boolean;
  onLoadMore: () => void;
  /** Action de l'état vide d'un journal sans aucune entrée (ouvrir la capture). */
  onEmptyAction: () => void;
}

/**
 * Le journal groupé par semaine (la plus récente d'abord, le bilan hebdomadaire en tête), filtré
 * par type, avec « Voir les entrées plus anciennes » tant que le serveur en a d'autres.
 */
export function JournalList(props: JournalListProps) {
  const { entries, kind, onKindChange, hasMore, loadingMore, onLoadMore, onEmptyAction } = props;
  const weeks = useMemo(() => groupByWeek(entries), [entries]);
  return (
    <div className="flex flex-col gap-4">
      <KindFilter value={kind} onChange={onKindChange} />
      {entries.length === 0 ? (
        <EmptyState
          title={t(kind ? "capture.journal.emptyFilterTitle" : "capture.journal.emptyTitle")}
          description={kind ? undefined : t("capture.journal.emptyDescription")}
          action={
            kind
              ? { label: t("capture.journal.emptyFilterAction"), onClick: () => onKindChange(null) }
              : { label: t("capture.journal.emptyAction"), onClick: onEmptyAction }
          }
        />
      ) : (
        <div role="group" aria-label={t("capture.journal.weeks")} className="flex flex-col gap-5">
          {weeks.map((week) => (
            <section key={week.weekStart} aria-labelledby={`journal-week-${week.weekStart}`}>
              <h2 id={`journal-week-${week.weekStart}`} className="mb-2 text-lg font-semibold">
                {t("capture.journal.week", { day: longDay(week.weekStart) })}
              </h2>
              <ul className="flex flex-col gap-2">
                {week.entries.map((entry) => (
                  <JournalEntry key={entry.id} entry={entry} />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
      {hasMore ? (
        <Button
          variant="outline"
          disabled={loadingMore}
          onClick={onLoadMore}
          className="self-start"
        >
          {loadingMore ? t("capture.journal.loadingMore") : t("capture.journal.more")}
        </Button>
      ) : null}
    </div>
  );
}
