import { t } from "@/shared/i18n/t";
import { ExternalLink } from "@/shared/ui/ExternalLink";
import type { OfferItemView } from "../viewTypes";

interface OffersCardProps {
  items: OfferItemView[];
}

/** Les nouvelles offres du radar : titre (lien extérieur), entreprise et score écrit « score 78 sur 100 ». */
export function OffersCard({ items }: OffersCardProps) {
  return (
    <section
      aria-labelledby="home-offers"
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <h2 id="home-offers" className="text-lg font-medium">
        {t("home.offers.title")}
      </h2>
      {items.length === 0 ? (
        <p className="text-muted-foreground">{t("home.offers.none")}</p>
      ) : (
        <ul aria-label={t("home.offers.listLabel")} className="flex flex-col gap-2 text-sm">
          {items.map((offer) => (
            <li key={offer.url} className="flex flex-col">
              <ExternalLink href={offer.url}>
                {offer.title ?? t("home.offers.untitled")}
              </ExternalLink>
              {offer.company ? (
                <span className="text-muted-foreground">{offer.company}</span>
              ) : null}
              <span className="tabular-nums">{t("home.offers.score", { score: offer.score })}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
