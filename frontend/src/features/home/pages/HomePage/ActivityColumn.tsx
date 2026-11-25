import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ActivityFeed } from "../../components/ActivityFeed";
import { useActivity } from "../../hooks/useActivity";

/** The activity feed as a column: its first page, « Voir plus » and its errors. */
export function ActivityColumn() {
  const activity = useActivity();
  const { query } = activity;
  if (query.isPending) return <LoadingState label={t("home.activity.loading")} />;
  if (query.isError && !query.data) {
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  return (
    <div className="flex flex-col gap-3">
      <ActivityFeed
        items={activity.items}
        hasMore={activity.hasMore}
        loadingMore={activity.loadingMore}
        onMore={activity.loadMore}
      />
      {activity.moreError ? (
        <InlineError message={errorMessage(activity.moreError)} onRetry={activity.loadMore} />
      ) : null}
    </div>
  );
}
