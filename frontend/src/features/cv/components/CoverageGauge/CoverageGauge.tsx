import { t } from "@/shared/i18n/t";

interface CoverageGaugeProps {
  /** Couverture des exigences du CV d'origine, de 0 à 100. */
  before: number;
  /** Couverture du CV généré, ou `null` tant qu'il n'existe pas. */
  after: number | null;
}

const clamp = (value: number): number => Math.min(100, Math.max(0, Math.round(value)));

/**
 * « Couverture des exigences : 58 % → 83 % » : la part des exigences obligatoires de l'offre que
 * le CV mentionne, avec un fait du profil derrière. La barre montre la valeur courante, un repère
 * marque le point de départ.
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
