import { t } from "@/shared/i18n/t";
import type { ProgramOption } from "../../api";

type Props = {
  options: ProgramOption[];
  selected: string[];
  onToggle: (id: string, checked: boolean) => void;
};

export function ProgramChoices({ options, selected, onToggle }: Props) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend>{t("interprogramPlanning.choose")}</legend>
      {options.map(({ id, title }) => (
        <label key={id} className="flex items-baseline gap-2">
          <input
            type="checkbox"
            checked={selected.includes(id)}
            disabled={selected.length >= 5 && !selected.includes(id)}
            onChange={(event) => onToggle(id, event.target.checked)}
          />
          {title}
        </label>
      ))}
    </fieldset>
  );
}
