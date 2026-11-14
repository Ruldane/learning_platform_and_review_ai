import { useMemo } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { ReviewDiff } from "../../components/ReviewDiff";
import type { DecideOptions, DecisionView } from "../../components/viewTypes";
import { useBulkDecide, useDecide } from "../../hooks/useDecide";
import { useProfile } from "../../hooks/useProfile";
import { factLabels } from "../../profileView";
import { toModificationViews } from "../../toView";
import type { CvReviewOut } from "../../types";
import { InlineError } from "@/shared/ui/states/InlineError";

const PENDING_DRAFT = "profile_draft_pending";

/**
 * Les modifications à décider. Une décision unitaire part seule ; « Tout accepter » ne prend que
 * les modifications `proposed` : celles « à confirmer » restent à décider une par une. Les faits
 * cités reprennent le texte du profil validé. Une revue terminée fige tout.
 */
export function DiffSection({ review, locked }: { review: CvReviewOut; locked: boolean }) {
  const decide = useDecide(review.id);
  const bulk = useBulkDecide(review.id);
  const profile = useProfile();
  const labels = useMemo(
    () => (profile.data?.validated ? factLabels(profile.data.validated.data) : new Map()),
    [profile.data],
  );
  const mods = useMemo(
    () => toModificationViews(review.modifications, labels),
    [review.modifications, labels],
  );
  const onDecide = (id: string, status: DecisionView, opts?: DecideOptions) =>
    decide.decide(id, { status, ...opts });
  const onBulk = (status: DecisionView) => {
    const ids = review.modifications
      .filter((mod) => mod.status === "proposed")
      .map((mod) => mod.id);
    if (ids.length > 0) bulk.decide(ids, status);
  };
  const error = decide.error ?? bulk.error;
  return (
    <div className="flex flex-col gap-3">
      {locked ? <p className="text-sm text-muted-foreground">{t("cv.reviewPage.closed")}</p> : null}
      <ReviewDiff
        mods={mods}
        onDecide={onDecide}
        onBulk={onBulk}
        busy={locked || decide.pending || bulk.pending}
      />
      {error ? <InlineError message={error} /> : null}
      {decide.code === PENDING_DRAFT ? (
        <Link to="/carriere/profil" className="text-sm font-medium underline underline-offset-4">
          {t("cv.reviewPage.draftLink")}
        </Link>
      ) : null}
    </div>
  );
}
