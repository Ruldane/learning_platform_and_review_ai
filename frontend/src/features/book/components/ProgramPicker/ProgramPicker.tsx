import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";

interface PickerProps {
  active: string;
  programs: readonly { id: string; title: string }[];
  onPick: (id: string) => void;
}

export function ProgramPicker({ active, programs, onPick }: PickerProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {t("book.program.label")}
      </label>
      <select
        id={id}
        value={active}
        onChange={(event) => onPick(event.target.value)}
        className={fieldClass}
      >
        <option value="">{t("book.program.pick")}</option>
        {programs.map((program) => (
          <option key={program.id} value={program.id}>
            {program.title}
          </option>
        ))}
      </select>
    </div>
  );
}
