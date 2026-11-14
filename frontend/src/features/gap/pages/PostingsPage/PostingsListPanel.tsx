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
  /** Action de l'état vide : mener au formulaire d'ajout. */
  onAdd: () => void;
}

const hrefOf = (postingId: string) => `/carriere/offres/${postingId}`;

/**
 * La liste des offres : chargement, erreur avec « Réessayer », état vide avec action, puis les
 * offres. Une relecture ratée garde la liste déjà affichée.
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
