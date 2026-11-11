import { t } from "@/shared/i18n/t";
import { authorLabel } from "../authorLabel";
import { formatDayTime } from "../formatDate";
import { formatShare } from "../format";
import { MEMORY_KINDS } from "../kindColors";
import { KindBadge } from "../KindBadge";
import type { MemoryStatsView } from "../viewTypes";
import { ReindexBlock } from "./ReindexBlock";
import { StatFigure } from "./StatFigure";
import { StatsLinks } from "./StatsLinks";

interface MemoryStatsProps {
  stats: MemoryStatsView;
  exportUrl: string;
  /** Vrai pendant la demande de réindexation (avant que le serveur ne la rapporte). */
  reindexPending: boolean;
  onReindex: () => void;
}

/** Statistiques de la mémoire : comptes, dernière écriture, quota Vectorize, réindexation, export. */
export function MemoryStats({ stats, exportUrl, reindexPending, onReindex }: MemoryStatsProps) {
  const { last_write: lastWrite, unindexed_items: unindexed } = stats;
  return (
    <section className="flex flex-col gap-4">
      <dl className="grid grid-cols-3 gap-3">
        <StatFigure label={t("memory.stats.items")} value={stats.total_items} />
        <StatFigure label={t("memory.stats.chunks")} value={stats.total_chunks} />
        <StatFigure label={t("memory.stats.pending")} value={stats.pending_decisions} />
      </dl>
      <ul aria-label={t("memory.stats.byKind")} className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {MEMORY_KINDS.map((kind) => (
          <li key={kind} className="flex items-center justify-between gap-2">
            <KindBadge kind={kind} />
            <span className="font-medium">{stats.by_kind[kind]}</span>
          </li>
        ))}
      </ul>
      <p className="text-sm">
        {lastWrite
          ? t("memory.stats.lastWrite", {
              author: authorLabel(lastWrite.author),
              date: formatDayTime(lastWrite.created_at),
            })
          : t("memory.stats.noWrite")}
      </p>
      <p className="text-sm">
        {t("memory.stats.quota", { share: formatShare(stats.vectorize_share) })}
      </p>
      {unindexed > 0 ? (
        <p className="text-sm font-medium text-destructive">
          {t(unindexed === 1 ? "memory.stats.unindexedOne" : "memory.stats.unindexedMany", {
            n: unindexed,
          })}
        </p>
      ) : null}
      <ReindexBlock reindex={stats.reindex} pending={reindexPending} onReindex={onReindex} />
      <StatsLinks exportUrl={exportUrl} dashboardUrl={stats.dashboard_url} />
    </section>
  );
}
