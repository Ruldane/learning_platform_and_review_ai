import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { listReading, type ReadFilter, type ReadingKind } from "../../api";
import { readingKeys } from "../../queryKeys";
import { ReadingEntry } from "./ReadingEntry";
import { ReadingFilters } from "./ReadingFilters";
import { ReadingList } from "./ReadingList";
import { ReadingSources } from "./ReadingSources";

export function ReadingPage() {
  const { itemId } = useParams();
  const [filter, setFilter] = useState<{
    state: ReadFilter;
    kind: ReadingKind | "";
    offset: number;
  }>({ state: "unread", kind: "", offset: 0 });
  const query = useQuery({
    queryKey: [...readingKeys.items, filter],
    queryFn: ({ signal }) => listReading(filter, signal),
  });
  const unread = query.data?.unread_count;
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t("reading.title")}</h1>
      {unread !== undefined ? (
        <p role="status" className="text-sm text-muted-foreground">
          {unread === 1 ? t("reading.countOne") : t("reading.count", { count: unread })}
        </p>
      ) : null}
      <ReadingSources />
      <ReadingFilters
        state={filter.state}
        kind={filter.kind}
        onState={(state) => setFilter({ ...filter, state, offset: 0 })}
        onKind={(kind) => setFilter({ ...filter, kind, offset: 0 })}
      />
      <div className="grid min-w-0 items-start gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        {query.isPending ? <LoadingState label={t("reading.articlesLoading")} /> : null}
        {query.isError ? (
          <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
        ) : null}
        {query.data ? (
          <ReadingList
            items={query.data.items}
            offset={filter.offset}
            next={query.data.next_offset}
            onPage={(offset) => setFilter({ ...filter, offset })}
          />
        ) : null}
        {itemId ? <ReadingEntry key={itemId} id={itemId} /> : null}
      </div>
    </div>
  );
}
