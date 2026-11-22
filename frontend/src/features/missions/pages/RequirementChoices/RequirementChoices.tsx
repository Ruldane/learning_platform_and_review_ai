import { t } from "@/shared/i18n/t";

type Props = {
  labels: string[];
  chosen: number[];
  disabled: boolean;
  onToggle: (index: number, selected: boolean) => void;
};

export function RequirementChoices({ labels, chosen, disabled, onToggle }: Props) {
  return (
    <fieldset className="flex flex-col gap-2" disabled={disabled}>
      <legend>{t("missions.requirements")}</legend>
      {labels.map((label, index) => (
        <label key={index} className="flex items-baseline gap-2">
          <input
            type="checkbox"
            checked={chosen.includes(index)}
            disabled={!chosen.includes(index) && chosen.length === 3}
            onChange={({ target }) => onToggle(index, target.checked)}
          />
          {label}
        </label>
      ))}
    </fieldset>
  );
}
