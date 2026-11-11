import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { SearchBench } from "../../components/SearchBench";
import type { MemoryKindView } from "../../components/viewTypes";
import { ImportEmptyState } from "../ImportEmptyState";
import { useMemorySearch } from "../../hooks/useMemorySearch";

interface Run {
  query: string;
  kinds: MemoryKindView[];
  k: number;
}

/** Banc d'essai : exactement les fragments (et le texte) qu'un agent recevrait pour une requête. */
export function SearchBenchPage() {
  const search = useMemorySearch();
  const [last, setLast] = useState<Run | null>(null);

  const run = (next: Run) => {
    setLast(next);
    search.mutate(next);
  };
  const empty = search.data !== undefined && search.data.hits.length === 0;

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold">{t("memory.page.benchTitle")}</h1>
      </header>
      <SearchBench
        result={search.data ?? null}
        pending={search.isPending}
        onRun={(query, kinds, k) => run({ query, kinds, k })}
      />
      {search.isError ? (
        <ErrorState
          message={errorMessage(search.error)}
          onRetry={() => (last ? run(last) : undefined)}
        />
      ) : null}
      {empty ? <ImportEmptyState title={t("memory.empty")} /> : null}
    </div>
  );
}
