import { t } from "@/shared/i18n/t";
import type { ArchitectureMeasures, ComparisonView } from "../viewTypes";

const number = new Intl.NumberFormat("en-GB");
const percentage = new Intl.NumberFormat("en-GB", { style: "percent", maximumFractionDigits: 2 });
const euros = new Intl.NumberFormat("en-GB", { style: "currency", currency: "EUR" });
const ARCHITECTURES = [
  ["first", "decisionLab.architectureA"],
  ["second", "decisionLab.architectureB"],
] as const;

function stats(value: ArchitectureMeasures) {
  const rate = value.servedFraction;
  return [
    [t("decisionLab.served"), number.format(value.served)],
    [t("decisionLab.missed"), number.format(value.missed)],
    [t("decisionLab.availability"), rate === null
      ? t("decisionLab.notApplicable") : percentage.format(rate)],
    [t("decisionLab.cost"), euros.format(value.costEuros)],
  ];
}

export function ComparisonResults({ value }: { value: ComparisonView }) {
  return (
    <section className="flex flex-col gap-3" aria-labelledby="decision-results" aria-live="polite">
      <h2 id="decision-results" tabIndex={-1} className="text-lg font-semibold">
        {t("decisionLab.results")}
      </h2>
      <p>{t("decisionLab.attempted")} · {number.format(value.attempted)}</p>
      <div className="grid gap-4 md:grid-cols-2">
        {ARCHITECTURES.map(([key, labelKey]) => (
          <section className="rounded-lg border border-border p-4" key={key}>
            <h3 className="mb-2 font-semibold">{t(labelKey)}</h3>
            <dl className="space-y-2">
              {stats(value[key]).map(([label, amount]) => (
                <div key={label} className="grid grid-cols-[1fr_auto] gap-3">
                  <dt>{label}</dt>
                  <dd className="font-medium tabular-nums">{amount}</dd>
                </div>
              ))}
            </dl>
          </section>
        ))}
      </div>
    </section>
  );
}
