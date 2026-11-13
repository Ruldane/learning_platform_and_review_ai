import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useCaptureDialog } from "../../captureDialog";
import { JournalList } from "../../components/JournalList";
import type { JournalKindView } from "../../components/viewTypes";
import { useJournal } from "../../hooks/useJournal";

/**
 * Le journal d'apprentissage (`/etudier/journal`) : captures, sessions d'étude, quiz et bilans
 * hebdomadaires, groupés par semaine ; filtre par type et pagination par `before`.
 */
export function JournalPage() {
  const [kind, setKind] = useState<JournalKindView | null>(null);
  const { query, entries } = useJournal(kind);
  const openCapture = useCaptureDialog((state) => state.openDialog);

  return (
    <div className="flex flex-col gap-4">
      <header>
        <h1 className="text-2xl font-semibold">{t("capture.journal.title")}</h1>
        <p className="mt-1 text-muted-foreground">{t("capture.journal.intro")}</p>
      </header>
      {query.isPending ? <LoadingState label={t("capture.journal.loading")} /> : null}
      {query.isError && !query.data ? (
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      ) : null}
      {query.data ? (
        <>
          <JournalList
            entries={entries}
            kind={kind}
            onKindChange={setKind}
            hasMore={query.hasNextPage}
            loadingMore={query.isFetchingNextPage}
            onLoadMore={() => void query.fetchNextPage()}
            onEmptyAction={openCapture}
          />
          {query.isError ? <InlineError message={errorMessage(query.error)} /> : null}
        </>
      ) : null}
    </div>
  );
}
