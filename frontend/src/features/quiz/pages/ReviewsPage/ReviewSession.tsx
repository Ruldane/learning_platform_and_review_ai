import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { FlashcardReview } from "../../components/FlashcardReview";
import { ReviewQueueHeader } from "../../components/ReviewQueueHeader";
import { useReviewCard } from "../../hooks/useReviews";
import { toCardView } from "../../toView";
import type { DueQueue } from "../../types";
import { ReviewDone } from "./ReviewDone";

/**
 * La file du jour, fiche après fiche. Une fiche passe quand son avis est enregistré (ou qu'elle a
 * déjà été revue : 409 `card_not_due`, sans erreur) ; un échec réseau la laisse en place.
 */
export function ReviewSession({ queue }: { queue: DueQueue }) {
  const review = useReviewCard();
  const [done, setDone] = useState<string[]>([]);
  const [demoted, setDemoted] = useState<string | null>(null);
  const cards = queue.cards.map(toCardView);
  const current = cards.find((card) => !done.includes(card.id));
  const later = queue.remaining_due;

  const answer = async (result: "ok" | "fail") => {
    if (!current) return;
    const outcome = await review.send(current.id, result);
    if (!outcome?.advanced) return;
    setDone((ids) => [...ids, current.id]);
    setDemoted(outcome.demotedSkill);
  };

  return (
    <div className="flex flex-col gap-4">
      {current ? (
        <ReviewQueueHeader
          remaining={cards.length - done.length}
          reviewedToday={queue.reviewed_today + done.length}
          dailyCards={queue.daily_cards}
        />
      ) : null}
      {review.error ? <InlineError message={review.error} /> : null}
      {demoted ? (
        <p role="status" className="rounded-lg border border-border bg-card px-3 py-2 text-sm">
          {t("quiz.reviews.demoted", { skill: demoted })}
        </p>
      ) : null}
      {current ? (
        <FlashcardReview
          key={current.id}
          card={current}
          busy={review.pending}
          onResult={(result) => void answer(result)}
        />
      ) : (
        <ReviewDone />
      )}
      {later > 0 ? (
        <p className="text-sm text-muted-foreground">
          {t(later === 1 ? "quiz.reviews.laterOne" : "quiz.reviews.laterMany", { count: later })}
        </p>
      ) : null}
    </div>
  );
}
