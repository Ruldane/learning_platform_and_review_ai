import { t } from "@/shared/i18n/t";
import type { RadarOfferView } from "../viewTypes";
import { OfferRow } from "./OfferRow";

interface RadarOffersProps {
  offers: RadarOfferView[];
}

/** Les offres lues par le relevé, avec leur score écrit ; à partir de 70, le libellé « Bon match ». */
export function RadarOffers({ offers }: RadarOffersProps) {
  return (
    <section aria-labelledby="radar-offers" className="flex flex-col gap-2">
      <h2 id="radar-offers" className="text-lg font-medium">
        {t("radar.offers.title")}
      </h2>
      {offers.length === 0 ? (
        <p className="text-muted-foreground">{t("radar.offers.none")}</p>
      ) : (
        <ul aria-label={t("radar.offers.label")} className="flex flex-col gap-2">
          {offers.map((offer) => (
            <OfferRow key={offer.url} offer={offer} />
          ))}
        </ul>
      )}
    </section>
  );
}
