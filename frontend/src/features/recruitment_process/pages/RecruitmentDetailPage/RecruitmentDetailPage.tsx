import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { answerStep, detailKey, readCase, type Step } from "../../api";
import { CaseContext } from "./CaseContext";
import { StepCard } from "./StepCard";

function useRehearsal(id: string) {
  return useQuery({
    queryKey: detailKey(id),
    queryFn: ({ signal }) => readCase(id, signal),
    refetchInterval: ({ state }) => state.data?.state === "evaluating" ? 750 : false,
  });
}

export function RecruitmentDetailPage() {
  const { processId = "" } = useParams();
  const query = useRehearsal(processId);
  const queries = useQueryClient();
  const status = useRef<HTMLParagraphElement>(null);
  const submit = useMutation({
    mutationFn: ({ kind, answer }: { kind: Step["kind"]; answer: string }) => answerStep(processId, kind, answer),
    onSuccess: async () => {
      await queries.invalidateQueries({ queryKey: detailKey(processId) });
    },
  });
  const row = query.data;
  return (
    <section className="grid max-w-3xl gap-5">
      <Link to="/carriere/recrutement-simule" className="w-fit underline">{t("recruitmentProcess.back")}</Link>
      {query.isPending ? <LoadingState label={t("recruitmentProcess.loading")} /> : null}
      {query.error ? <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} /> : null}
      {row ? <>
        <h1 className="text-2xl font-semibold">{row.posting_title}</h1>
        <p tabIndex={-1} role="status" ref={status}>{t(`recruitmentProcess.status.${row.state}`)}</p>
        <CaseContext row={row} />
        {row.steps.map((step) => (
          <StepCard key={step.kind} step={step} rubric={row.rubric} active={row.active_step === step.kind}
            pending={row.state === "evaluating" || submit.isPending} retry={row.state === "failed"}
            onAnswer={(answer) => {
              status.current?.focus();
              submit.mutate({ kind: step.kind, answer });
            }} />
        ))}
      </> : null}
      {submit.error ? <InlineError message={errorMessage(submit.error)} /> : null}
    </section>
  );
}
