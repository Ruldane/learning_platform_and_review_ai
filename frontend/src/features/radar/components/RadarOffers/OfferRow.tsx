import { CheckCircle2 } from "lucide-react";
import { t } from "@/shared/i18n/t";
import { ExternalLink } from "@/shared/ui/ExternalLink";
import type { RadarOfferView } from "../viewTypes";

/** The score at which a posting counts as a good match (`HIGH_MATCH` on the server). */
const GOOD_MATCH = 70;

const KNOWN_LEVELS = ["junior", "mid_level", "senior", "lead"] as const;

function details(offer: RadarOfferView): string[] {
  const known = KNOWN_LEVELS.find((level) => level === offer.level);
  return [
    known ? t(`radar.offers.level.${known}`) : null,
    offer.remote ? t("radar.offers.remote", { remote: offer.remote }) : null,
    offer.salary ? t("radar.offers.salary", { salary: offer.salary }) : null,
  ].filter((part): part is string => Boolean(part));
}

/** Show the posting link, company, match score and details found in the source. */
export function OfferRow({ offer }: { offer: RadarOfferView }) {
  const good = offer.score >= GOOD_MATCH;
  const facts = details(offer);
  return (
    <li
      data-good-match={good}
      className={`flex flex-col gap-1 rounded-xl border bg-card p-3 text-sm ${good ? "border-primary" : ""}`}
    >
      <ExternalLink href={offer.url}>{offer.title ?? t("radar.offers.untitled")}</ExternalLink>
      {offer.company ? <span className="text-muted-foreground">{offer.company}</span> : null}
      <span className="flex flex-wrap items-center gap-2">
        <span className="tabular-nums">{t("radar.offers.score", { score: offer.score })}</span>
        {good ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-primary px-2 py-0.5 text-xs font-medium text-primary-foreground">
            <CheckCircle2 aria-hidden="true" className="size-3" />
            {t("radar.offers.goodMatch")}
          </span>
        ) : null}
      </span>
      {facts.length > 0 ? <span className="text-muted-foreground">{facts.join(" · ")}</span> : null}
    </li>
  );
}
