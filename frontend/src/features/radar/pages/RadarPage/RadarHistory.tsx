import type { UseQueryResult } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import type { HistoryItemView } from "../../toView";
import { HistoryRow } from "./HistoryRow";

interface RadarHistoryProps {
  history: UseQueryResult<HistoryItemView[]>;
  /** The sweep shown above, marked in the list. */
  currentId: string | null;
}

/** The sweep history (last 20, most recent first): each one opens in place. */
export function RadarHistory({ history, currentId }: RadarHistoryProps) {
  let body;
  if (history.isPending) body = <LoadingState label={t("radar.history.loading")} />;
  else if (history.isError) {
    body = (
      <ErrorState message={errorMessage(history.error)} onRetry={() => void history.refetch()} />
    );
  } else if (history.data.length === 0) {
    body = <p className="text-muted-foreground">{t("radar.history.empty")}</p>;
  } else {
    body = (
      <ol aria-label={t("radar.history.label")} className="flex flex-col gap-2">
        {history.data.map((item) => (
          <HistoryRow key={item.id} item={item} current={item.id === currentId} />
        ))}
      </ol>
    );
  }
  return (
    <section aria-labelledby="radar-history" className="flex flex-col gap-2">
      <h2 id="radar-history" className="text-lg font-medium">
        {t("radar.history.title")}
      </h2>
      {body}
    </section>
  );
}
