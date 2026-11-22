import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { basePath, createExperiment, listExperiments, watchKey } from "../../api";
import { ExperimentForm } from "../../components/ExperimentForm";

export function WatchPage() {
  const cache = useQueryClient();
  const navigate = useNavigate();
  const history = useQuery({
    queryKey: watchKey,
    queryFn: ({ signal }) => listExperiments(signal),
  });
  const create = useMutation({
    mutationFn: createExperiment,
    onSuccess: (item) => {
      void cache.invalidateQueries({ queryKey: watchKey });
      void navigate(`${basePath}/${item.id}`);
    },
  });
  return (
    <main className="mx-auto grid max-w-3xl gap-4 p-4">
      <h1 className="text-2xl font-semibold">{t("contradictoryWatch.title")}</h1>
      <p>{t("contradictoryWatch.intro")}</p>
      {create.isError && <InlineError message={errorMessage(create.error)} />}
      <ExperimentForm onCreate={create.mutate} pending={create.isPending} />
      <section className="grid gap-2">
        <h2 className="text-lg font-semibold">{t("contradictoryWatch.history")}</h2>
        {history.isPending && <LoadingState label={t("contradictoryWatch.loading")} />}
        {history.isError && (
          <ErrorState
            message={errorMessage(history.error)}
            onRetry={() => void history.refetch()}
          />
        )}
        {history.data?.length === 0 && <p>{t("contradictoryWatch.empty")}</p>}
        <ul className="list-disc pl-5">
          {history.data?.map((item) => (
            <li key={item.id}>
              <Link className="underline" to={`${basePath}/${item.id}`}>
                {item.title}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
