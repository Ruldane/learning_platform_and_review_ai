import type { UseQueryResult } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import type { PostingChoiceView } from "../../components/viewTypes";
import type { PostingSummaryOut } from "../../types";
import { ChosenPostingCompare } from "./ChosenPostingCompare";

interface PostingCompareProps {
  postings: UseQueryResult<PostingSummaryOut[]>;
  choices: PostingChoiceView[];
  postingId: string | null;
}

/**
 * La comparaison avec une offre : chargement de la liste, erreur avec « Réessayer », état vide
 * avec action quand aucune offre n'est analysée, invitation à choisir, puis le tableau.
 */
export function PostingCompare({ postings, choices, postingId }: PostingCompareProps) {
  const navigate = useNavigate();
  if (postings.isError) {
    return (
      <ErrorState message={errorMessage(postings.error)} onRetry={() => void postings.refetch()} />
    );
  }
  if (postings.data === undefined) {
    return <LoadingState label={t("skills.compare.postingsLoading")} />;
  }
  if (choices.length === 0) {
    return (
      <EmptyState
        title={t("skills.compare.noPostingsTitle")}
        description={t("skills.compare.noPostingsDescription")}
        action={{
          label: t("skills.compare.noPostingsAction"),
          onClick: () => void navigate("/carriere/offres"),
        }}
      />
    );
  }
  if (postingId === null) {
    return <p className="text-sm text-muted-foreground">{t("skills.compare.pickPosting")}</p>;
  }
  return <ChosenPostingCompare postingId={postingId} />;
}
