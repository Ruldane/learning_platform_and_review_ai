import { useEffect, useRef } from "react";
import { useLocation, useNavigate, useParams } from "react-router";
import { t } from "@/shared/i18n/t";
import { isRunSource } from "@/shared/lib/runSource";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { cvErrorMessage } from "../../errors";
import { useStartReview } from "../../hooks/useStartReview";
import { ReviewRefusal } from "./ReviewRefusal";

/**
 * Starts the CV review for a posting (`/career/cv/reviews/new/:postingId`). The back end checks
 * validated profile, active template and analyzed posting: each refusal (409) has text and action
 * (« Valide ton profil », « Crée ton modèle »…). An already open review for the posting is resumed.
 * Otherwise `POST /cv/reviews`, then redirect to the review.
 */
export function NewReviewPage() {
  const { postingId = "" } = useParams();
  const navigate = useNavigate();
  const state: unknown = useLocation().state;
  const source =
    state !== null && typeof state === "object" && "runSource" in state
      ? state.runSource
      : undefined;
  const { start, refusal, error } = useStartReview(
    postingId,
    (reviewId) => void navigate(`/career/cv/reviews/${reviewId}`, { replace: true }),
    isRunSource(source) ? source : undefined,
  );
  const launched = useRef(false);

  useEffect(() => {
    // A single launch per visit, even if React replays the effect.
    if (launched.current) return;
    launched.current = true;
    start();
  }, [start]);

  const reusing = refusal?.code === "review_in_progress" && refusal.reviewId !== null;
  if (refusal === null || reusing) return <LoadingState label={t("cv.newReview.loading")} />;
  return (
    <ReviewRefusal
      code={refusal.code}
      postingId={postingId}
      fallback={<ErrorState message={cvErrorMessage(error)} onRetry={() => start()} />}
    />
  );
}
