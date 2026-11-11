import { t } from "@/shared/i18n/t";
import type { SourcesViewModel } from "../sourceTypes";
import { QueryList } from "./QueryList";
import { SourceList } from "./SourceList";

interface SourcesPanelProps {
  model: SourcesViewModel;
  /** La recherche n'est pas finie : « L'Éclaireur cherche… », annoncé aux lecteurs d'écran. */
  pending: boolean;
}

/**
 * Ce que la recherche web a trouvé : les requêtes lancées, puis les sources retenues, écartées
 * (avec la raison) et illisibles. Présentationnel : la page lui passe un modèle de vue (D34).
 */
export function SourcesPanel({ model, pending }: SourcesPanelProps) {
  const { queries, kept, rejected, unreadable } = model;
  const empty = queries.length + kept.length + rejected.length + unreadable.length === 0;
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
    </section>
  );
}
