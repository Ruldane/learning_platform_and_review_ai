import { useQuery } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { evidenceKey, getEvidence } from "../../api";
import { ObservationForm } from "../ObservationForm";

export function ObservationSetup() {
  const evidence = useQuery({
    queryKey: evidenceKey,
    queryFn: ({ signal }) => getEvidence(signal),
  });
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-lg font-semibold">{t("errorAtlas.newObservation")}</h2>
      {evidence.isPending && <LoadingState />}
      {evidence.isError && (
        <ErrorState
          message={errorMessage(evidence.error)}
          onRetry={() => void evidence.refetch()}
        />
      )}
      {evidence.data?.length === 0 && <p>{t("errorAtlas.noEvidence")}</p>}
      {evidence.data && evidence.data.length > 0 && <ObservationForm evidence={evidence.data} />}
    </section>
  );
}
