import { errorMessage } from "@/shared/api/errors";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { exportUrl } from "../../api";
import { MemoryStats } from "../../components/MemoryStats";
import { useMemoryStats, useReindex } from "../../hooks/useMemoryStats";

/** Statistiques de la mémoire, avec Réindexer (suivi toutes les 2 s) et l'export JSON. */
export function StatsSection() {
  const stats = useMemoryStats();
  const reindex = useReindex();

  if (stats.isError) {
    return <ErrorState message={errorMessage(stats.error)} onRetry={() => void stats.refetch()} />;
  }
  if (!stats.data) return <LoadingState />;
  return (
    <div className="flex flex-col gap-2">
      <MemoryStats
        stats={stats.data}
        exportUrl={exportUrl}
        reindexPending={reindex.isPending}
        onReindex={() => reindex.mutate()}
      />
      {reindex.isError ? <InlineError message={errorMessage(reindex.error)} /> : null}
    </div>
  );
}
