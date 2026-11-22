import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { OfferDetails } from "../../api";
import { OfferRequirement } from "./OfferRequirement";

export function OfferGapForm({
  rows,
  busy,
  onSubmit,
}: {
  rows: OfferDetails["rows"];
  busy: boolean;
  onSubmit: (skills: string[]) => void;
}) {
  const [chosen, setChosen] = useState<string[]>([]);
  return (
    <form
      className="grid gap-4"
      onSubmit={(event) => { event.preventDefault(); if (chosen.length) onSubmit(chosen); }}
    >
      <fieldset className="grid gap-3">
        <legend className="mb-2 font-semibold">{t("compatibleOffers.skills")}</legend>
        <ul className="grid gap-3">
          {rows.map((row) => {
            const selected = chosen.includes(row.skill);
            return (
              <OfferRequirement
                key={row.skill}
                row={row}
                selected={selected}
                locked={busy || (!selected && chosen.length >= 10)}
                onChange={() => setChosen((current) => selected
                  ? current.filter((skill) => skill !== row.skill) : [...current, row.skill])}
              />
            );
          })}
        </ul>
      </fieldset>
      <Button className="justify-self-start" disabled={!chosen.length || busy} type="submit">
        {t("compatibleOffers.plan")}
      </Button>
    </form>
  );
}
