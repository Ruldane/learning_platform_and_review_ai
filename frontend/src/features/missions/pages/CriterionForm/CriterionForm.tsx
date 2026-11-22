import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { Criterion } from "../../api";
import { useCriterionDraft, type Changes } from "../MissionCriterion/criterionDraft";

type Props = {
  criterion: Criterion;
  working: boolean;
  onSave: (progress: Changes, onSaved: () => void) => void;
};

export function CriterionForm({ criterion, working, onSave }: Props) {
  const { observed, note, changed, setDraft, clearSavedDraft } = useCriterionDraft(criterion);
  return (
    <form
      className="mt-3 flex flex-col gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (!working && changed) onSave({ observed, note }, clearSavedDraft);
      }}
    >
      <label className="flex gap-2">
        {t("missions.observed")}
        <select
          className="rounded border border-border bg-background px-2"
          value={observed}
          onChange={(event) => setDraft({ observed: Number(event.target.value), note })}
        >
          <option value={0}>{t("missions.observed0")}</option>
          <option value={1}>{t("missions.observed1")}</option>
          <option value={2}>{t("missions.observed2")}</option>
        </select>
      </label>
      <label className="flex flex-col">
        {t("missions.note")}
        <textarea
          className="rounded border border-border bg-background p-2"
          maxLength={2000}
          rows={2}
          value={note}
          onChange={(event) => setDraft({ observed, note: event.target.value })}
        />
      </label>
      <Button type="submit" className="self-start" aria-disabled={working || !changed}>
        {t("missions.save")}
      </Button>
    </form>
  );
}
