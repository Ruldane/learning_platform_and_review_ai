import type { ReactNode } from "react";
import { useNavigate } from "react-router";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { t } from "@/shared/i18n/t";

interface ReviewRefusalProps {
  /** The refusal code from the back end. */
  code: string;
  postingId: string;
  /** A refusal with no clean follow-up: the failure and its « Réessayer ». */
  fallback: ReactNode;
}

/** A refusal to launch the review, with the right action to recover; otherwise `fallback`. */
export function ReviewRefusal({ code, postingId, fallback }: ReviewRefusalProps) {
  const navigate = useNavigate();
  const to = (path: string) => () => void navigate(path);
  switch (code) {
    case "profile_required":
      return (
        <EmptyState
          title={t("cv.newReview.profileTitle")}
          description={t("cv.newReview.profileHint")}
          action={{ label: t("cv.newReview.profileAction"), onClick: to("/career/profile") }}
        />
      );
    case "template_required":
      return (
        <EmptyState
          title={t("cv.newReview.templateTitle")}
          description={t("cv.newReview.templateHint")}
          action={{ label: t("cv.newReview.templateAction"), onClick: to("/career/cv") }}
        />
      );
    case "posting_not_ready":
      return (
        <EmptyState
          title={t("cv.newReview.notReadyTitle")}
          description={t("cv.newReview.notReadyHint")}
          action={{
            label: t("cv.newReview.postingAction"),
            onClick: to(`/career/postings/${postingId}`),
          }}
        />
      );
    case "posting_not_found":
      return (
        <EmptyState
          title={t("cv.newReview.notFoundTitle")}
          action={{ label: t("cv.newReview.postingsAction"), onClick: to("/career/postings") }}
        />
      );
    default:
      return fallback;
  }
}
