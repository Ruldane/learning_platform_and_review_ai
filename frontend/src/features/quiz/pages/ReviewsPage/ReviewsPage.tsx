import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useDueCards } from "../../hooks/useReviews";
import { ReviewSession } from "./ReviewSession";

/** Révisions (`/etudier/revisions`) : la file du jour (30 fiches, 15 minutes), une fiche à la fois. */
export function ReviewsPage() {
  const due = useDueCards();
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-4">
      <header>
        <h1 className="text-2xl font-semibold">{t("quiz.reviews.title")}</h1>
        <p className="mt-1 text-muted-foreground">{t("quiz.reviews.intro")}</p>
      </header>
      {due.isPending ? <LoadingState label={t("quiz.reviews.loading")} /> : null}
      {due.isError ? (
        <ErrorState message={errorMessage(due.error)} onRetry={() => void due.refetch()} />
      ) : null}
      {due.data ? <ReviewSession queue={due.data} /> : null}
    </div>
  );
}
