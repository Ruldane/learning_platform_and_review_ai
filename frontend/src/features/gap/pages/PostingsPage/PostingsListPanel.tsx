import { useMemo } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { PostingList } from "../../components/PostingList";
import { usePostings } from "../../hooks/usePostings";
import { toPostingListItems } from "../../toView";

interface PostingsListPanelProps {
  pollMs: number;
  /** Empty-state action: leads to the add form. */
  onAdd: () => void;
}

const hrefOf = (postingId: string) => `/career/postings/${postingId}`;

/**
 * The postings list: loading, error with « Réessayer », empty state with action, then the
 * postings. A failed re-read keeps the list already shown.
 */
export function PostingsListPanel({ pollMs, onAdd }: PostingsListPanelProps) {
  const { query } = usePostings(pollMs);
  const items = useMemo(() => (query.data ? toPostingListItems(query.data) : null), [query.data]);
  if (items === null) {
    if (query.isError) {
      return (
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      );
    }
    return <LoadingState label={t("gap.postings.loading")} />;
  }
  if (items.length === 0) {
    return (
      <EmptyState
        title={t("gap.postings.emptyTitle")}
        description={t("gap.postings.emptyDescription")}
        action={{ label: t("gap.postings.emptyAction"), onClick: onAdd }}
      />
    );
  }
  return <PostingList postings={items} hrefOf={hrefOf} />;
}
