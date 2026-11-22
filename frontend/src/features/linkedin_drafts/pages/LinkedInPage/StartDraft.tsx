import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

export function StartDraft({
  offers,
  busy,
  onStart,
}: {
  offers: { id: string; title: string | null }[];
  busy: boolean;
  onStart: (id: string) => void;
}) {
  const [target, setTarget] = useState("");
  return (
    <form
      className="grid gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (!busy) onStart(target);
      }}
    >
      <label className="grid gap-1">
        <span>{t("linkedInDrafts.target")}</span>
        <select className="rounded-md border bg-background p-2" value={target}
          onChange={(event) => setTarget(event.target.value)}>
          <option value="">{t("linkedInDrafts.all")}</option>
          {offers.map((offer) => <option key={offer.id} value={offer.id}>{offer.title}</option>)}
        </select>
      </label>
      <Button aria-disabled={busy} className="justify-self-start" type="submit">
        {t("linkedInDrafts.prepare")}
      </Button>
    </form>
  );
}
