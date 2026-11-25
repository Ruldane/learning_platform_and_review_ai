import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { createRun, evaluateRun, listOptions, listRuns } from "../../api";
import { BlindForm } from "../../components/BlindForm";
import { BlindRunCard } from "./BlindRunCard";

const RUNS = ["blind-assessment", "runs"] as const;
function useAssessmentRuns() {
  return useQuery({
    queryKey: RUNS,
    queryFn: ({ signal }) => listRuns(signal),
    refetchInterval: ({ state }) =>
      state.data?.some((item) => item.stage === "evaluating") ? 750 : false,
  });
}

function useCreateRun() {
  const queries = useQueryClient();
  return useMutation({
    mutationFn: createRun,
    onSuccess: () => queries.invalidateQueries({ queryKey: RUNS }),
  });
}

function useAssessmentOptions() {
  return useQuery({
    queryKey: ["blind-assessment", "options"],
    queryFn: ({ signal }) => listOptions(signal),
  });
}

export function BlindAssessmentPage() {
  const queries = useQueryClient();
  const history = useRef<HTMLHeadingElement>(null);
  const options = useAssessmentOptions();
  const runs = useAssessmentRuns();
  const create = useCreateRun();
  const launch = useMutation({
    mutationFn: evaluateRun,
    onSuccess: async () => {
      history.current?.focus();
      await queries.invalidateQueries({ queryKey: RUNS });
    },
  });
  const sourceOptions = options.data?.sources.map(({ id, label }) => ({ id, title: label }));
  return (
    <section className="grid max-w-3xl gap-5">
      <h1 className="text-2xl font-semibold">{t("blindAssessment.title")}</h1>
      {options.isPending || runs.isPending ? <LoadingState label={t("blindAssessment.loading")} /> : null}
      {options.error ? <ErrorState message={errorMessage(options.error)} onRetry={() => void options.refetch()} /> : null}
      {sourceOptions && sourceOptions.length < 2 ? (
        <p>
          {t("blindAssessment.insufficient")}{" "}
          <Link className="underline" to="/career/cv/versions">
            {t("blindAssessment.versions")}
          </Link>
        </p>
      ) : null}
      {options.data && sourceOptions && sourceOptions.length >= 2 ? (
        <BlindForm
          sources={sourceOptions}
          rubrics={options.data.rubrics}
          busy={create.isPending}
          onSubmit={(first, second, grid) => {
            const rubric = options.data?.rubrics.find((item) => item.id === grid);
            if (rubric) create.mutate({ first_version_id: first, second_version_id: second, rubric: rubric.id });
          }}
        />
      ) : null}
      {create.error ? <InlineError message={errorMessage(create.error)} /> : null}
      {create.isSuccess ? <p role="status">{t("blindAssessment.saved")}</p> : null}
      <h2 ref={history} tabIndex={-1} className="text-lg font-semibold">{t("blindAssessment.history")}</h2>
      {runs.error ? <ErrorState message={errorMessage(runs.error)} onRetry={() => void runs.refetch()} /> : null}
      {launch.error ? <InlineError message={errorMessage(launch.error)} /> : null}
      {runs.data?.length === 0 ? <p>{t("blindAssessment.empty")}</p> : null}
      {runs.data?.map((run) => (
        <BlindRunCard key={run.id} run={run} busy={launch.isPending} evaluate={() => launch.mutate(run.id)} />
      ))}
    </section>
  );
}
