import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { AssumptionsForm } from "../../components/AssumptionsForm";
import { ComparisonResults } from "../../components/ComparisonResults";
import { SaveScenarioForm } from "../../components/SaveScenarioForm";
import { ScenarioHistory } from "../../components/ScenarioHistory";
import { assumptionsIn } from "../../toView";
import { useDecisionLab } from "./useDecisionLab";

function focusResults() {
  requestAnimationFrame(() => document.getElementById("decision-results")?.focus());
}

export function DecisionLabPage() {
  const lab = useDecisionLab();
  const busy = lab.comparison.isPending || lab.saved.isPending || lab.opened.isPending;
  const error = lab.comparison.error ?? lab.saved.error ?? lab.opened.error ?? lab.history.error;
  return (
    <section className="flex max-w-4xl flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("decisionLab.title")}</h1>
      <p className="text-muted-foreground">{t("decisionLab.model")}</p>
      <AssumptionsForm
        value={lab.assumptions} onChange={lab.setAssumptions} busy={busy}
        onCompare={() => {
          lab.saved.reset();
          lab.comparison.mutate(lab.assumptions, { onSuccess: focusResults });
        }}
      />
      {lab.result && <>
        <ComparisonResults value={lab.result} />
        <SaveScenarioForm
          title={lab.title} critique={lab.critique} onTitle={lab.setTitle}
          onCritique={lab.setCritique} busy={busy}
          onSave={() => lab.saved.mutate({
            title: lab.title, critique: lab.critique, assumptions: assumptionsIn(lab.assumptions),
          })}
        />
      </>}
      {lab.saved.isSuccess && <p role="status">{t("decisionLab.saved")}</p>}
      {error && <InlineError message={errorMessage(error)} />}
      {lab.history.isPending && <LoadingState />}
      {lab.history.data && (
        <ScenarioHistory
          scenarios={lab.history.data} busy={busy}
          onOpen={(id) => lab.opened.mutate(id, { onSuccess: focusResults })}
        />
      )}
    </section>
  );
}
