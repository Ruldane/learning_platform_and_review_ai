import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { AgentCallList } from "../../components/AgentCallList";
import { CallFilters } from "../../components/CallFilters";
import { useAgentCalls } from "../../hooks/useAgentCalls";

/**
 * Settings > Agent log: calls to the models, newest first, filtered
 * by agent and by graph, page after page. The filters are part of the read key: changing
 * them starts from the first page; they stay shown during the read (focus kept).
 */
export function AgentLogPage() {
  const [agent, setAgent] = useState<string | null>(null);
  const [graph, setGraph] = useState<string | null>(null);
  const { query, calls } = useAgentCalls(agent, graph);
  return (
    <div className="flex flex-col gap-4">
      <header>
        <h1 className="text-2xl font-semibold">{t("costs.log.title")}</h1>
        <p className="mt-1 text-muted-foreground">{t("costs.log.intro")}</p>
      </header>
      <CallFilters agent={agent} graph={graph} onAgentChange={setAgent} onGraphChange={setGraph} />
      {query.isPending ? <LoadingState label={t("costs.log.loading")} /> : null}
      {query.isError && !query.data ? (
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      ) : null}
      {query.data ? (
        <>
          <AgentCallList
            calls={calls}
            filtered={agent !== null || graph !== null}
            hasMore={query.hasNextPage}
            loadingMore={query.isFetchingNextPage}
            onLoadMore={() => void query.fetchNextPage()}
          />
          {query.isError ? (
            <InlineError
              message={errorMessage(query.error)}
              // Re-read what failed: the next page, or (failed re-read) the pages shown.
              onRetry={() =>
                void (query.isFetchNextPageError ? query.fetchNextPage() : query.refetch())
              }
            />
          ) : null}
        </>
      ) : null}
    </div>
  );
}
