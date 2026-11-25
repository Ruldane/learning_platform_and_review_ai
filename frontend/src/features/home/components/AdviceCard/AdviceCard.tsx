import { t } from "@/shared/i18n/t";
import type { AdviceStatus } from "../viewTypes";

interface AdviceCardProps {
  /** The two sentences of the advice, once it is ready. */
  sentences: string[] | null;
  status: AdviceStatus;
}

/**
 * Today's advice. `pending`: still gathering (the only state that changes). `failed` and
 * `unavailable`: the advice could say nothing for the whole day, whatever the cause,
 * and with no « Réessayer » button: the server does not rerun the advice that day.
 */
export function AdviceCard({ sentences, status }: AdviceCardProps) {
  const ready = status === "ready" && sentences !== null && sentences.length > 0;
  return (
    <section
      aria-labelledby="home-advice"
      className="flex flex-col gap-2 rounded-xl border bg-card p-4"
    >
      <h2 id="home-advice" className="text-lg font-medium">
        {t("home.advice.title")}
      </h2>
      {/* Polite live region, always there: the arrival (or failure) of the advice is announced. */}
      <div aria-live="polite" className="flex flex-col gap-2">
        {ready ? (
          sentences.map((sentence, index) => <p key={`${index}-${sentence}`}>{sentence}</p>)
        ) : status === "pending" ? (
          <p className="text-muted-foreground">{t("home.advice.pending")}</p>
        ) : (
          <p className="text-muted-foreground">{t("home.advice.unavailable")}</p>
        )}
      </div>
    </section>
  );
}
