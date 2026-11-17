import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { ProviderOption } from "../viewTypes";

interface ProviderSelectProps {
  /** Étiquette lue par les lecteurs d'écran (le champ n'a pas de texte visible). */
  label: string;
  value: string;
  options: ProviderOption[];
  disabled?: boolean;
  /** Texte d'un premier choix « aucun » (valeur vide) : pour une option facultative. */
  emptyLabel?: string;
  onPick: (provider: string) => void;
}

function optionLabel(option: ProviderOption) {
  return option.has_key ? option.label : t("settings.tiers.noKeyOption", { label: option.label });
}

/** Liste des fournisseurs ; ceux sans clé sont marqués « aucune clé » mais restent choisissables. */
export function ProviderSelect({
  label,
  value,
  options,
  disabled = false,
  emptyLabel,
  onPick,
}: ProviderSelectProps) {
  const id = useId();
  const known =
    options.some((option) => option.name === value) || (value === "" && emptyLabel !== undefined);
  return (
    <>
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <select
        id={id}
        className={`${fieldClass} sm:max-w-48`}
        value={value}
        disabled={disabled}
        onChange={(event) => onPick(event.target.value)}
      >
        {emptyLabel === undefined ? null : <option value="">{emptyLabel}</option>}
        {known ? null : <option value={value}>{value}</option>}
        {options.map((option) => (
          <option key={option.name} value={option.name}>
            {optionLabel(option)}
          </option>
        ))}
      </select>
    </>
  );
}
