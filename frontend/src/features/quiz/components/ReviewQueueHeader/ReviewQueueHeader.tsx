import { t } from "@/shared/i18n/t";

interface ReviewQueueHeaderProps {
  /** Fiches encore dues. */
  remaining: number;
  reviewedToday: number;
  /** Plafond du jour : 30 fiches, soit 15 minutes. */
  dailyCards: number;
}

function remainingText(count: number): string {
  if (count <= 0) return t("quiz.queue.remainingNone");
  return t(count === 1 ? "quiz.queue.remainingOne" : "quiz.queue.remainingMany", { count });
}

/** En-tête de la file du jour : fiches restantes, fiches revues sur le plafond, « 15 min max ». */
export function ReviewQueueHeader({
  remaining,
  reviewedToday,
  dailyCards,
}: ReviewQueueHeaderProps) {
  const done = Math.min(Math.max(reviewedToday, 0), dailyCards);
  const percent = dailyCards > 0 ? (done / dailyCards) * 100 : 0;
  return (
    <section
      aria-label={t("quiz.queue.label")}
      className="flex flex-col gap-2 rounded-xl border bg-card p-4"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-lg font-semibold">{remainingText(remaining)}</p>
        <p className="text-sm text-muted-foreground">{t("quiz.queue.cap")}</p>
      </div>
      <div
        role="progressbar"
        aria-label={t("quiz.queue.progress")}
        aria-valuemin={0}
        aria-valuemax={dailyCards}
        aria-valuenow={done}
        className="h-2 overflow-hidden rounded-full bg-muted"
      >
        <div className="h-full bg-primary" style={{ width: `${percent}%` }} />
      </div>
      <p className="text-sm text-muted-foreground tabular-nums">
        {t("quiz.queue.reviewed", { done: reviewedToday, max: dailyCards })}
      </p>
    </section>
  );
}
