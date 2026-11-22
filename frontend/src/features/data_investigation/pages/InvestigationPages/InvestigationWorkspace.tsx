import { useMutation, useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import {
  investigationsKey,
  readInvestigation,
  submitInvestigation,
  updateOperations,
} from "../../api";
import { ConclusionForm, ConclusionResult } from "../../components/Conclusion";
import { OperationsPanel } from "../../components/OperationsPanel";
import { SourceRows } from "../../components/SourceRows";

type Study = Awaited<ReturnType<typeof readInvestigation>>;

function useInvestigationActions(study: Study) {
  const cache = useQueryClient();
  const updateCache = (item: Study) => cache.setQueryData([...investigationsKey, study.id], item);
  const edit = useMutation({
    mutationFn: (operations: Study["operations"]) => updateOperations(study.id, operations),
    onSuccess: updateCache,
  });
  const submit = useMutation({
    mutationFn: (result: Parameters<typeof submitInvestigation>[1]) =>
      submitInvestigation(study.id, result),
    onSuccess: updateCache,
  });
  return {
    edit,
    submit,
    busy: edit.isPending || submit.isPending,
    error: edit.error ?? submit.error,
  };
}

export function InvestigationWorkspace({ study }: { study: Study }) {
  const { edit, submit, busy, error } = useInvestigationActions(study);
  return (
    <>
      <h1 className="text-2xl font-semibold">{study.dataset.title}</h1>
      <p>{study.dataset.brief}</p>
      <SourceRows
        source={study.source_rows}
        retained={study.retained_rows}
        digest={study.source_digest}
      />
      <OperationsPanel
        trace={study.trace}
        editable={!study.result}
        busy={busy}
        onChange={edit.mutate}
      />
      <p role="status">
        {t("dataInvestigation.preview", {
          deliveries: study.preview.deliveries,
          units: study.preview.units,
        })}
      </p>
      {error && <InlineError message={errorMessage(error)} />}
      {study.result ? (
        <ConclusionResult
          integrity={study.result.integrity_passed}
          matches={study.result.matches_pipeline}
          expected={study.result.expected}
          focus={submit.isSuccess}
        />
      ) : (
        <ConclusionForm
          pending={busy}
          onSubmit={(deliveries, units) => submit.mutate({ deliveries, units })}
        />
      )}
    </>
  );
}
