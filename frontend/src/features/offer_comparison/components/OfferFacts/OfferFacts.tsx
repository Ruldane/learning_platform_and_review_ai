import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { OfferFactsView } from "../viewTypes";

export function OfferFacts({ view }: { view: OfferFactsView }) {
  return (
    <article className="grid gap-2 rounded border p-3">
      <h3 className="font-medium">{view.heading}</h3>
      {view.company ? <p>{view.company}</p> : null}
      <p>{t("offerComparison.score")} · {view.score}</p>
      <dl className="grid gap-1 text-sm">
        {view.facts.map(({ label, value }) => (
          <div key={label}><dt className="inline font-medium">{label} · </dt><dd className="inline">{value}</dd></div>
        ))}
      </dl>
      <p className="text-sm">{view.missing}</p>
      <Link className="w-fit underline" to={view.source}>{t("offerComparison.source")}</Link>
    </article>
  );
}
