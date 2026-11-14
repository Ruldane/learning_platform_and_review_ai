import { useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { cvErrorMessage } from "../../errors";
import { useStartReview } from "../../hooks/useStartReview";
import { ReviewRefusal } from "./ReviewRefusal";

/**
 * Lancer la revue du CV pour une offre (`/carriere/cv/revue/nouvelle/:postingId`). Le back vérifie le
 * profil validé, le modèle actif et l'offre analysée : chaque refus (409) a son texte et son action
 * (« Valide ton profil », « Crée ton modèle »…). Une revue déjà ouverte pour l'offre est reprise.
 * Sinon `POST /cv/reviews`, puis redirection vers la revue.
 */
export function NewReviewPage() {
  const { postingId = "" } = useParams();
  const navigate = useNavigate();
  const { start, refusal, error } = useStartReview(
    postingId,
    (reviewId) => void navigate(`/carriere/cv/revues/${reviewId}`, { replace: true }),
  );
  const launched = useRef(false);

  useEffect(() => {
    // Un seul lancement par visite, même si React rejoue l'effet.
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
