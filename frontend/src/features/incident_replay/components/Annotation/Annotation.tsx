import type { FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface Props {
  pending: boolean;
  saved: boolean;
  onSave: (hypothesis: string) => void;
}

export function Annotation({ pending, saved, onSave }: Props) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const hypothesis = String(new FormData(event.currentTarget).get("hypothesis") ?? "").trim();
    if (hypothesis && !pending) onSave(hypothesis);
  }
  return (
    <form onSubmit={submit} className="grid gap-3">
      <label className="grid gap-1">
        {t("incidentReplay.hypothesis")}
        <textarea
          name="hypothesis"
          className="rounded border bg-background p-2"
          maxLength={1500}
          required
        />
      </label>
      <Button type="submit" aria-disabled={pending}>
        {t("incidentReplay.record")}
      </Button>
      {saved && <p role="status">{t("incidentReplay.saved")}</p>}
    </form>
  );
}
