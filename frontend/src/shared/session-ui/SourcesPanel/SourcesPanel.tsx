import { t } from "@/shared/i18n/t";
import type { SourcesViewModel } from "../sourceTypes";
import { PeopleList } from "./PeopleList";
import { QueryList } from "./QueryList";
import { SourceList } from "./SourceList";

interface SourcesPanelProps {
  model: SourcesViewModel;
  /** Search not finished: « L'Éclaireur cherche… », announced to screen readers. */
  pending: boolean;
}

/**
 * What the web search found: the queries run, then the sources kept, discarded
 * (with the reason) and unreadable. Presentational: the page passes it a view model (D34).
 */
export function SourcesPanel({ model, pending }: SourcesPanelProps) {
  const { queries, kept, rejected, unreadable, people } = model;
  const empty =
    queries.length + kept.length + rejected.length + unreadable.length + people.length === 0;
  return (
    <section aria-label={t("session.sources.label")} className="flex flex-col gap-4">
      <p role="status" aria-live="polite" className="text-sm text-muted-foreground">
        {pending ? t("session.sources.pending") : null}
      </p>
      {empty && !pending ? (
        <p className="text-sm text-muted-foreground">{t("session.sources.empty")}</p>
      ) : null}
      <QueryList queries={queries} />
      <SourceList title={t("session.sources.kept")} sources={kept} />
      <SourceList title={t("session.sources.rejected")} sources={rejected} />
      <SourceList title={t("session.sources.unreadable")} sources={unreadable} />
      <PeopleList people={people} />
    </section>
  );
}
