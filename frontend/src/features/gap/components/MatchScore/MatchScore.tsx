import { t } from "@/shared/i18n/t";

interface MatchScoreProps {
  /** Match score from 0 to 100 (rounded and clamped here). */
  score: number;
}

/**
 * A posting's match score: « 62/100 », a gauge and its written name. A hint to get
 * a sense of fit, never a hiring promise (the text says so).
 */
export function MatchScore({ score }: MatchScoreProps) {
  const value = Math.min(100, Math.max(0, Math.round(score)));
  return (
    <section className="flex flex-col gap-2 rounded-xl border bg-card p-4">
      <h3 className="text-sm font-medium text-muted-foreground">{t("gap.score.title")}</h3>
      <p className="text-3xl font-semibold tabular-nums">
        {t("gap.score.value", { score: value })}
      </p>
      <div
        role="meter"
        aria-label={t("gap.score.label", { score: value })}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
        className="h-2 overflow-hidden rounded-full bg-muted"
      >
        <div className="h-full rounded-full bg-primary" style={{ width: `${value}%` }} />
      </div>
      <p className="text-xs text-muted-foreground">{t("gap.score.hint")}</p>
    </section>
  );
}
