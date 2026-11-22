import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { DecisionFields } from "../DecisionFields";
import { IndicatorFields } from "../IndicatorFields";
import { useCommitmentDraft } from "./useCommitmentDraft";

export function CommitmentForm() {
  const { draft, change, create } = useCommitmentDraft();
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (!create.isPending) create.mutate();
      }}
    >
      <h2 className="text-lg font-semibold">{t("datedCommitments.plan")}</h2>
      <DecisionFields draft={draft} onChange={change} />
      <IndicatorFields draft={draft} onChange={change} />
      {create.isError && <p role="alert">{errorMessage(create.error)}</p>}
      <Button type="submit" className="self-start" aria-disabled={create.isPending}>
        {t("datedCommitments.create")}
      </Button>
    </form>
  );
}
