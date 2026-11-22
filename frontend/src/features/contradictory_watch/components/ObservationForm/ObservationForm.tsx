import type { FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { outcomes, type Outcome } from "../viewTypes";

interface Props {
  pending: boolean;
  onRecord: (measurement: string, outcome: Outcome) => void;
}

export function ObservationForm({ pending, onRecord }: Props) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const outcome = outcomes.find((item) => item === form.get("outcome"));
    if (outcome) onRecord(String(form.get("measurement")).trim(), outcome);
  }

  return (
    <form className="grid gap-3" onSubmit={submit}>
      <label className="grid gap-1">
        {t("contradictoryWatch.measurement")}
        <textarea
          name="measurement"
          className="rounded border bg-background p-2"
          maxLength={3000}
          required
        />
      </label>
      <label className="grid gap-1">
        {t("contradictoryWatch.outcome")}
        <select name="outcome" className="rounded border bg-background p-2" defaultValue="" required>
          <option value="" disabled>{t("contradictoryWatch.selectOutcome")}</option>
          {outcomes.map((outcome) => (
            <option key={outcome} value={outcome}>
              {t(`contradictoryWatch.outcomes.${outcome}`)}
            </option>
          ))}
        </select>
      </label>
      <Button type="submit" disabled={pending}>
        {t("contradictoryWatch.record")}
      </Button>
    </form>
  );
}
