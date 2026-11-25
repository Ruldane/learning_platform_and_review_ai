import { t } from "@/shared/i18n/t";

interface CoverageGaugeProps {
  /** Coverage of the requirements in the original CV, from 0 to 100. */
  before: number;
  /** Coverage of the generated CV, or `null` until it exists. */
  after: number | null;
}

const clamp = (value: number): number => Math.min(100, Math.max(0, Math.round(value)));

/**
 * « Couverture des exigences : 58 % → 83 % »: the share of the offer's mandatory requirements
 * that the CV mentions, backed by a profile fact. The bar shows the current value; a marker
 * marks the starting point.
 */
export function CoverageGauge({ before, after }: CoverageGaugeProps) {
  const start = clamp(before);
  const current = after === null ? start : clamp(after);
  const text =
    after === null
      ? t("cv.coverage.label", { before: start })
      : t("cv.coverage.change", { before: start, after: current });
  return (
    <section className="flex flex-col gap-2 rounded-xl border bg-card p-4">
      <p className="text-lg font-semibold tabular-nums">{text}</p>
      <div
        role="meter"
        aria-label={text}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={current}
        className="relative h-2 overflow-hidden rounded-full bg-muted"
      >
        <div className="h-full rounded-full bg-primary" style={{ width: `${current}%` }} />
        {after === null ? null : (
          <span
            aria-hidden="true"
            className="absolute inset-y-0 w-0.5 bg-foreground"
            style={{ left: `${start}%` }}
          />
        )}
      </div>
      <p className="text-xs text-muted-foreground">{t("cv.coverage.hint")}</p>
    </section>
  );
}
