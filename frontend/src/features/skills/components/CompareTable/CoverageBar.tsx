import { t } from "@/shared/i18n/t";

/** La couverture du poste cible : le chiffre et une barre de progression. */
export function CoverageBar({ coverage }: { coverage: number }) {
  const percent = Math.min(Math.max(coverage, 0), 100);
  return (
    <div className="flex flex-col gap-2">
      <p className="text-lg font-semibold">{t("skills.compare.coverage", { coverage: percent })}</p>
      <div
        role="progressbar"
        aria-label={t("skills.compare.coverageBar")}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        className="h-2 overflow-hidden rounded-full bg-muted"
      >
        <div className="h-full bg-primary" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
