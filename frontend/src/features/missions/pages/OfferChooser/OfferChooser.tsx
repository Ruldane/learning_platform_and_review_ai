import { useQuery } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { fetchReadyOffers, type Mission } from "../../api";
import { OfferLink } from "../OfferLink";

export function OfferChooser({ missions }: { missions: Mission[] }) {
  const offers = useQuery({
    queryKey: ["missions", "offers"],
    queryFn: ({ signal }) => fetchReadyOffers(signal),
  });
  const used = new Set(missions.map((mission) => mission.posting_id));
  const available = offers.data?.filter(({ id }) => !used.has(id));
  return (
    <div className="flex flex-col gap-4">
      {missions.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold">{t("missions.history")}</h2>
          <ul className="list-inside list-disc">
            {missions.map((mission) => (
              <OfferLink key={mission.id} id={mission.posting_id} title={mission.posting_title} />
            ))}
          </ul>
        </section>
      )}
      <section>
        <h2 className="text-lg font-semibold">{t("missions.chooseOffer")}</h2>
        {offers.isPending && <LoadingState />}
        {offers.isError && (
          <ErrorState message={errorMessage(offers.error)} onRetry={() => void offers.refetch()} />
        )}
        {available?.length === 0 && <p>{t("missions.empty")}</p>}
        {available && available.length > 0 && (
          <ul className="list-inside list-disc">
            {available.map((offer) => (
              <OfferLink key={offer.id} id={offer.id} title={offer.title} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
