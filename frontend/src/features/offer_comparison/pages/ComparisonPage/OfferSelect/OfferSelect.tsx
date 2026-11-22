import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { SourceOffer } from "../../../api";

interface OptionProps {
  label: string;
  value: string;
  options: SourceOffer[];
  excluded: string;
  onChange: (id: string) => void;
}

export function OfferSelect({ label, value, options, excluded, onChange }: OptionProps) {
  const id = useId();
  return (
    <label htmlFor={id} className="grid gap-1">
      {label}
      <select
        id={id}
        value={value}
        className={fieldClass}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{t("offerComparison.choose")}</option>
        {options.map((offer) => (
          <option key={offer.id} value={offer.id} disabled={offer.id === excluded}>
            {offer.title ?? t("offerComparison.unknownTitle")}
            {offer.company ? ` · ${offer.company}` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}
