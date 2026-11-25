import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { ExternalLink } from "@/shared/ui/ExternalLink";
import type { OfferItemView } from "../viewTypes";

interface OffersCardProps {
  items: OfferItemView[];
  /** Offers source down this morning: neither an empty list nor « aucune nouvelle offre ». */
  unavailable?: boolean;
}

/** New radar offers: title (external link), company and score written « score 78 sur 100 ». */
export function OffersCard({ items, unavailable = false }: OffersCardProps) {
  return (
    <section
      aria-labelledby="home-offers"
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <h2 id="home-offers" className="text-lg font-medium">
        {t("home.offers.title")}
      </h2>
      {unavailable ? (
        <p className="text-muted-foreground">{t("home.unavailable")}</p>
      ) : items.length === 0 ? (
        <p className="text-muted-foreground">{t("home.offers.none")}</p>
      ) : (
        <ul aria-label={t("home.offers.listLabel")} className="flex flex-col gap-2 text-sm">
          {items.map((offer, index) => (
            // Two offers can share a link: the position breaks the tie.
            <li key={`${offer.url}#${index}`} className="flex flex-col">
              <ExternalLink href={offer.url}>
                {offer.title ?? t("home.offers.untitled")}
              </ExternalLink>
              {offer.company ? (
                <span className="text-muted-foreground">{offer.company}</span>
              ) : null}
              <span className="tabular-nums">{t("home.offers.score", { score: offer.score })}</span>
              {offer.gapPath ? (
                <Link className="self-start underline underline-offset-4" to={offer.gapPath}>
                  {t("home.offers.gap", { title: offer.title ?? t("home.offers.untitled") })}
                </Link>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
