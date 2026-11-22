import { useQuery } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { getHypotheses, hypothesesKey } from "../../api";
import { HypothesisCard } from "../HypothesisCard";
import { ObservationSetup } from "../ObservationSetup";

export function ErrorAtlasPage() {
  const groups = useQuery({
    queryKey: hypothesesKey,
    queryFn: ({ signal }) => getHypotheses(signal),
  });

  return (
    <section className="flex max-w-3xl flex-col gap-6">
      <h1 className="text-2xl font-semibold">{t("errorAtlas.title")}</h1>
      <ObservationSetup />
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">{t("errorAtlas.hypotheses")}</h2>
        {groups.isPending && <LoadingState />}
        {groups.isError && (
          <ErrorState message={errorMessage(groups.error)} onRetry={() => void groups.refetch()} />
        )}
        {groups.data?.length === 0 && <p>{t("errorAtlas.empty")}</p>}
        {groups.data?.map((group) => (
          <HypothesisCard key={group.id} group={group} />
        ))}
      </section>
    </section>
  );
}
