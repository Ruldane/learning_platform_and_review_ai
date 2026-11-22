import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import {
  basePath, experimentKey, readExperiment, recordObservation, toFrozenWatch, type Observation,
} from "../../api";
import { FrozenExperiment } from "../../components/FrozenExperiment";
import { ObservationForm } from "../../components/ObservationForm";

export function WatchDetailPage() {
  const id = useParams().experimentId ?? "";
  const queryKey = experimentKey(id);
  const cache = useQueryClient();
  const experiment = useQuery({ queryKey, queryFn: ({ signal }) => readExperiment(id, signal) });
  const record = useMutation({
    mutationFn: (value: Observation) => recordObservation(id, value),
    onSuccess: (item) => cache.setQueryData(queryKey, item),
  });
  return (
    <main className="mx-auto grid max-w-3xl gap-4 p-4">
      <Link className="underline" to={basePath}>
        {t("contradictoryWatch.back")}
      </Link>
      {experiment.isPending && <LoadingState label={t("contradictoryWatch.loading")} />}
      {experiment.isError && (
        <ErrorState
          message={errorMessage(experiment.error)}
          onRetry={() => void experiment.refetch()}
        />
      )}
      {experiment.data && (
        <>
          <h1 className="text-2xl font-semibold">{experiment.data.title}</h1>
          <FrozenExperiment
            experiment={toFrozenWatch(experiment.data)}
            focusResult={record.isSuccess}
          />
          {record.isError && <InlineError message={errorMessage(record.error)} />}
          {experiment.data.status === "ready" && (
            <ObservationForm
              onRecord={(measurement, outcome) => record.mutate({ measurement, outcome })}
              pending={record.isPending}
            />
          )}
        </>
      )}
    </main>
  );
}
