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
 * Réglages > Journal des agents : les appels aux modèles, du plus récent au plus ancien, filtrés
 * par agent et par parcours, page après page. Les filtres sont dans la clé de la lecture : en
 * changer repart de la première page ; ils restent affichés pendant la lecture (focus gardé).
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
              // Relire ce qui a échoué : la page suivante, ou (relecture ratée) les pages affichées.
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
