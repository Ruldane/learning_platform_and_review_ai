import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { ProviderOption } from "../viewTypes";

interface ProviderSelectProps {
  /** Label read by screen readers (the field has no visible text). */
  label: string;
  value: string;
  options: ProviderOption[];
  disabled?: boolean;
  /** Text of a first « aucun » choice (empty value): for an optional option. */
  emptyLabel?: string;
  onPick: (provider: string) => void;
}

function optionLabel(option: ProviderOption) {
  return option.has_key ? option.label : t("settings.tiers.noKeyOption", { label: option.label });
}

/** List of providers; those without a key are marked « aucune clé » but stay selectable. */
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
