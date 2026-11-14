import { Link, useNavigate, useParams } from "react-router";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { POLL_MS } from "../../hooks/useProfile";
import { useReview } from "../../hooks/useReview";
import { ReviewBody } from "./ReviewBody";

interface ReviewPageProps {
  pollMs?: number;
  /** Ne sert qu'aux tests (faux WebSocket). */
  createSocket?: SocketFactory;
}

/**
 * Une revue du CV (`/carriere/cv/revues/:reviewId`), lue en une page : le fil des agents, les
 * indicateurs avant et après, les modifications à décider, le rapport, puis la sortie (voir le
 * rapport, générer le PDF, terminer) et l'aperçu de la dernière version.
 */
export function ReviewPage({ pollMs = POLL_MS, createSocket }: ReviewPageProps) {
  const { reviewId = "" } = useParams();
  const navigate = useNavigate();
  const query = useReview(reviewId, pollMs);
  const review = query.data;

  if (review === undefined) {
    if (query.error instanceof ApiError && query.error.status === 404) {
      return (
        <EmptyState
          title={t("cv.reviewPage.notFoundTitle")}
          description={t("cv.reviewPage.notFoundHint")}
          action={{
            label: t("cv.reviewPage.notFoundAction"),
            onClick: () => void navigate("/carriere/cv/versions"),
          }}
        />
      );
    }
    if (query.isError) {
      return (
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      );
    }
    return <LoadingState label={t("cv.reviewPage.loading")} />;
  }
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <nav className="flex flex-wrap gap-4 text-sm">
          <Link to={`/carriere/offres/${review.posting_id}`} className="underline">
            {t("cv.reviewPage.back")}
          </Link>
          <Link to="/carriere/cv/versions" className="underline">
            {t("cv.reviewPage.versionsLink")}
          </Link>
        </nav>
        <h1 className="text-2xl font-semibold">{t("cv.reviewPage.title")}</h1>
        <p role="status" className="text-muted-foreground">
          {t(`cv.reviewPage.status.${review.status}`)}
        </p>
      </header>
      <ReviewBody review={review} createSocket={createSocket} />
    </div>
  );
}
