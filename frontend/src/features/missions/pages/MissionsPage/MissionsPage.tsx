import { useQuery } from "@tanstack/react-query";
import { useRef } from "react";
import { useSearchParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { fetchMissions } from "../../api";
import { missionsKey } from "../../cache";
import { MissionDetail } from "../MissionDetail";
import { MissionSetup } from "../MissionSetup";
import { OfferChooser } from "../OfferChooser";

export function MissionsPage() {
  const [params, changeParams] = useSearchParams();
  const posting = params.get("posting") ?? params.get("offre");
  const heading = useRef<HTMLHeadingElement>(null);
  const history = useQuery({
    queryKey: missionsKey,
    queryFn: ({ signal }) => fetchMissions(signal),
  });
  const current = history.data?.find((mission) => mission.posting_id === posting);
  const chooseOffer = () => {
    heading.current?.focus();
    changeParams({});
  };

  return (
    <section className="flex max-w-3xl flex-col gap-6">
      <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold">
        {t("missions.title")}
      </h1>
      {history.isPending && <LoadingState />}
      {history.isError && (
        <ErrorState message={errorMessage(history.error)} onRetry={() => void history.refetch()} />
      )}
      {history.data && (
        <>
          {posting && (
            <button type="button" onClick={chooseOffer} className="self-start underline">
              {t("missions.newChoice")}
            </button>
          )}
          {!posting && <OfferChooser missions={history.data} />}
          {posting && !current && (
            <MissionSetup
              key={posting}
              postingId={posting}
              onCreated={() => heading.current?.focus()}
            />
          )}
          {current && <MissionDetail key={current.id} mission={current} />}
        </>
      )}
    </section>
  );
}
