import { t } from "@/shared/i18n/t";
import { OfferFacts } from "../OfferFacts";
import type { ComparisonView } from "../viewTypes";
import { WeightSensitivity } from "../WeightSensitivity";

export function ComparisonResult({ view }: { view: ComparisonView }) {
  return (
    <section className="grid gap-3 rounded-xl border bg-card p-4">
      <h2 className="text-lg font-semibold">{t("offerComparison.results")}</h2>
      <p role="status">{view.rank}</p>
      {view.criteria ? <p className="text-sm">{t("offerComparison.matched")} · {view.criteria}</p> : null}
      <div className="grid gap-3 sm:grid-cols-2">
        <OfferFacts view={view.first} />
        <OfferFacts view={view.second} />
      </div>
      <WeightSensitivity data={view.sensitivity} />
    </section>
  );
}
