import { t } from "@/shared/i18n/t";
import { fieldClass } from "../formStyles";

interface Props {
  label: string;
  value: string;
  disabled: boolean;
  options: { id: string; label: string }[];
  onChange: (id: string) => void;
  placeholder?: boolean;
}

export function ChoiceField({ label, value, disabled, options, onChange, placeholder }: Props) {
  return (
    <label className="w-full">
      {label}
      <select
        className={fieldClass}
        required
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        {placeholder ? <option value="">{t("calendar.chooseOption")}</option> : null}
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
