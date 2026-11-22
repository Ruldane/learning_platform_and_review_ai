import type { FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface Props {
  pending: boolean;
  onSubmit: (deliveries: number, units: number) => void;
}

export function ConclusionForm({ pending, onSubmit }: Props) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (!pending) onSubmit(Number(form.get("deliveries")), Number(form.get("units")));
  }
  return (
    <form className="grid gap-3" onSubmit={submit}>
      <label className="grid gap-1">
        {t("dataInvestigation.deliveries")}
        <input
          className="rounded border bg-background p-2"
          type="number"
          name="deliveries"
          min={0}
          max={1000}
          required
        />
      </label>
      <label className="grid gap-1">
        {t("dataInvestigation.units")}
        <input
          className="rounded border bg-background p-2"
          type="number"
          name="units"
          min={0}
          max={100000}
          required
        />
      </label>
      <Button type="submit" aria-disabled={pending}>
        {t("dataInvestigation.submit")}
      </Button>
    </form>
  );
}
