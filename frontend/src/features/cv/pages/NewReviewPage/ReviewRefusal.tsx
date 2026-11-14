import type { ReactNode } from "react";
import { useNavigate } from "react-router";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { t } from "@/shared/i18n/t";

interface ReviewRefusalProps {
  /** Le code du refus du back. */
  code: string;
  postingId: string;
  /** Un refus sans suite propre : la panne et son « Réessayer ». */
  fallback: ReactNode;
}

/** Un refus du lancement de la revue, avec la bonne action pour s'en sortir ; sinon `fallback`. */
export function ReviewRefusal({ code, postingId, fallback }: ReviewRefusalProps) {
  const navigate = useNavigate();
  const to = (path: string) => () => void navigate(path);
  switch (code) {
    case "profile_required":
      return (
        <EmptyState
          title={t("cv.newReview.profileTitle")}
          description={t("cv.newReview.profileHint")}
          action={{ label: t("cv.newReview.profileAction"), onClick: to("/carriere/profil") }}
        />
      );
    case "template_required":
      return (
        <EmptyState
          title={t("cv.newReview.templateTitle")}
          description={t("cv.newReview.templateHint")}
          action={{ label: t("cv.newReview.templateAction"), onClick: to("/carriere/cv") }}
        />
      );
    case "posting_not_ready":
      return (
        <EmptyState
          title={t("cv.newReview.notReadyTitle")}
          description={t("cv.newReview.notReadyHint")}
          action={{
            label: t("cv.newReview.postingAction"),
            onClick: to(`/carriere/offres/${postingId}`),
          }}
        />
      );
    case "posting_not_found":
      return (
        <EmptyState
          title={t("cv.newReview.notFoundTitle")}
          action={{ label: t("cv.newReview.postingsAction"), onClick: to("/carriere/offres") }}
        />
      );
    default:
      return fallback;
  }
}
