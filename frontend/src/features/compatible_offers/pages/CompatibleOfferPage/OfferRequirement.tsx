import { t } from "@/shared/i18n/t";
import type { OfferDetails } from "../../api";

type Requirement = OfferDetails["rows"][number];

export function OfferRequirement({
  row,
  selected,
  locked,
  onChange,
}: {
  row: Requirement;
  selected: boolean;
  locked: boolean;
  onChange: () => void;
}) {
  const mastered = row.level === "valide" || row.level === "prouve";
  const status = mastered ? "mastered" : row.week === null ? "missing" : "planned";
  return (
    <li className="grid gap-1">
      {status === "missing" ? (
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={selected} disabled={locked} onChange={onChange} />
          <span>{row.skill}</span>
        </label>
      ) : (
        <span>{row.skill}</span>
      )}
      <p className="flex flex-wrap gap-x-3 text-sm text-muted-foreground">
        <span>{t(row.required ? "compatibleOffers.required" : "compatibleOffers.preferred")}</span>
        <span>{t(`compatibleOffers.${status}`, { week: row.week ?? "" })}</span>
      </p>
    </li>
  );
}
