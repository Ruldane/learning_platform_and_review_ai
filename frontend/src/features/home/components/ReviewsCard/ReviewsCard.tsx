import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface ReviewsCardProps {
  /** The records in today's queue. */
  queue: number;
  /** Records due beyond today's queue. */
  remaining: number;
  onReview: () => void;
  /** The reviews source was down this morning: neither zero nor a button. */
  unavailable?: boolean;
}

/** Today's reviews: how many records, how many beyond the queue, and the « Réviser » button. */
export function ReviewsCard({ queue, remaining, onReview, unavailable = false }: ReviewsCardProps) {
  return (
    <section
      aria-labelledby="home-reviews"
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <h2 id="home-reviews" className="text-lg font-medium">
        {t("home.reviews.title")}
      </h2>
      {unavailable ? (
        <p className="text-muted-foreground">{t("home.unavailable")}</p>
      ) : queue === 0 ? (
        <p className="text-muted-foreground">{t("home.reviews.none")}</p>
      ) : (
        <p>
          {queue === 1
            ? t("home.reviews.queue.one")
            : t("home.reviews.queue.many", { count: queue })}
        </p>
      )}
      {!unavailable && remaining > 0 ? (
        <p className="text-sm text-muted-foreground">
          {remaining === 1
            ? t("home.reviews.remaining.one")
            : t("home.reviews.remaining.many", { count: remaining })}
        </p>
      ) : null}
      {!unavailable && queue > 0 ? (
        <Button className="self-start" onClick={onReview}>
          {t("home.reviews.start")}
        </Button>
      ) : null}
    </section>
  );
}
